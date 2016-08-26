/*
 * Copyright (C) 2016 Gustavo Sverzut Barbieri
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library;
 * if not, see <http://www.gnu.org/licenses/>.
 */

/* c-mode: linux-4 */
#include "curl-websocket.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <unistd.h>
#include <fcntl.h>
#include <ctype.h>
#include <inttypes.h>
#include <errno.h>

#include "curl-websocket-utils.c"

#define ERR(fmt, ...) \
    fprintf(stderr, "ERROR: " fmt "\n", ## __VA_ARGS__)

#define STR_OR_EMPTY(p) (p != NULL ? p : "")

/* Temporary buffer size to use during WebSocket masking.
 * stack-allocated
 */
#define CWS_MASK_TMPBUF_SIZE 4096

enum cws_opcode {
  CWS_OPCODE_CONTINUATION = 0x0,
  CWS_OPCODE_TEXT = 0x1,
  CWS_OPCODE_BINARY = 0x2,
  CWS_OPCODE_CLOSE = 0x8,
  CWS_OPCODE_PING = 0x9,
  CWS_OPCODE_PONG = 0xa,
};

/*
 * WebSocket is a framed protocol in the format:
 *
 *    0                   1                   2                   3
 *    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 *   +-+-+-+-+-------+-+-------------+-------------------------------+
 *   |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
 *   |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
 *   |N|V|V|V|       |S|             |   (if payload len==126/127)   |
 *   | |1|2|3|       |K|             |                               |
 *   +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
 *   |     Extended payload length continued, if payload len == 127  |
 *   + - - - - - - - - - - - - - - - +-------------------------------+
 *   |                               |Masking-key, if MASK set to 1  |
 *   +-------------------------------+-------------------------------+
 *   | Masking-key (continued)       |          Payload Data         |
 *   +-------------------------------- - - - - - - - - - - - - - - - +
 *   :                     Payload Data continued ...                :
 *   + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
 *   |                     Payload Data continued ...                |
 *   +---------------------------------------------------------------+
 *
 * See https://tools.ietf.org/html/rfc6455#section-5.2
 */
struct cws_frame_header {
    /* first byte: fin + opcode */
    uint8_t opcode : 4;
    uint8_t _reserved : 3;
    uint8_t fin : 1;

    /* second byte: mask + payload length */
    uint8_t payload_len : 7; /* if 126, uses extra 2 bytes (uint16_t)
                              * if 127, uses extra 8 bytes (uint64_t)
                              * if <=125 is self-contained
                              */
    uint8_t mask : 1; /* if 1, uses 4 extra bytes */
};

struct cws_data {
    CURL *easy;
    struct cws_callbacks cbs;
    struct {
        char *requested;
        char *received;
    } websocket_protocols;
    struct curl_slist *headers;
    char accept_key[29];
    struct {
        struct cws_frame_header frame_header;
        uint64_t frame_len; /* payload length for current frame */
        uint64_t total_len; /* total length (note fragmentation) */
        uint64_t used_len; /* total filled length (note fragmentation) */
        uint8_t *payload; /* full payload (note fragmentation) */

        uint8_t tmpbuf[sizeof(struct cws_frame_header) + sizeof(uint64_t)];
        uint8_t done; /* of tmpbuf, for header */
        uint8_t needed; /* of tmpbuf, for header */
    } recv;
    struct {
        uint8_t *buffer;
        size_t len;
    } send;
    uint8_t dispatching;
    uint8_t pause_flags;
    bool accepted;
    bool upgraded;
    bool connection_websocket;
    bool closed;
    bool deleted;
};

static bool _cws_write(struct cws_data *priv, const void *buffer, size_t len) {
    /* optimization note: we could grow by some rounded amount (ie:
     * next power-of-2, 4096/pagesize...) and if using
     * priv->send.position, do the memmove() here to free up some
     * extra space without realloc() (see _cws_send_data()).
     */
    //_cws_debug("WRITE", buffer, len);
    uint8_t *tmp = realloc(priv->send.buffer, priv->send.len + len);
    if (!tmp)
        return false;
    memcpy(tmp + priv->send.len, buffer, len);
    priv->send.buffer = tmp;
    priv->send.len += len;
    if (priv->pause_flags & CURLPAUSE_SEND) {
        priv->pause_flags &= ~CURLPAUSE_SEND;
        curl_easy_pause(priv->easy, priv->pause_flags);
    }
    return true;
}

/*
 * Mask is:
 *
 *     for i in len:
 *         output[i] = input[i] ^ mask[i % 4]
 *
 * Here a temporary buffer is used to reduce number of "write" calls
 * and pointer arithmetic to avoid counters.
 */
static bool _cws_write_masked(struct cws_data *priv, const uint8_t mask[static 4], const void *buffer, size_t len) {
    const uint8_t *itr_begin = buffer;
    const uint8_t *itr = itr_begin;
    const uint8_t *itr_end = itr + len;
    uint8_t tmpbuf[CWS_MASK_TMPBUF_SIZE];

    while (itr < itr_end) {
        uint8_t *o = tmpbuf, *o_end = tmpbuf + sizeof(tmpbuf);
        for (; o < o_end && itr < itr_end; o++, itr++) {
            *o = *itr ^ mask[(itr - itr_begin) & 0x3];
        }
        if (!_cws_write(priv, tmpbuf, o - tmpbuf))
            return false;
    }

    return true;
}

static bool _cws_send(struct cws_data *priv, enum cws_opcode opcode, const void *msg, size_t msglen) {
    struct cws_frame_header fh = {
        .fin = 1, /* TODO review if should fragment over some boundary */
        .opcode = opcode,
        .mask = 1,
        .payload_len = ((msglen > UINT16_MAX) ? 127 :
                        (msglen > 125) ? 126 : msglen),
    };
    uint8_t mask[4];

    if (priv->closed) {
        ERR("cannot send data to closed WebSocket connection %p", priv->easy);
        return false;
    }

    _cws_get_random(mask, sizeof(mask));

    if (!_cws_write(priv, &fh, sizeof(fh)))
        return false;

    if (fh.payload_len == 127) {
        uint64_t payload_len = msglen;
        _cws_hton(&payload_len, sizeof(payload_len));
        if (!_cws_write(priv, &payload_len, sizeof(payload_len)))
            return false;
    } else if (fh.payload_len == 126) {
        uint16_t payload_len = msglen;
        _cws_hton(&payload_len, sizeof(payload_len));
        if (!_cws_write(priv, &payload_len, sizeof(payload_len)))
            return false;
    }

    if (!_cws_write(priv, mask, sizeof(mask)))
        return false;

    return _cws_write_masked(priv, mask, msg, msglen);
}

bool cws_send(CURL *easy, bool text, const void *msg, size_t msglen) {
    struct cws_data *priv;
    char *p = NULL;

    curl_easy_getinfo(easy, CURLINFO_PRIVATE, &p); /* checks for char* */
    if (!p) {
        ERR("not CWS (no CURLINFO_PRIVATE): %p", easy);
        return false;
    }
    priv = (struct cws_data *)p;

    return _cws_send(priv, text ? CWS_OPCODE_TEXT : CWS_OPCODE_BINARY,
                     msg, msglen);
}

bool cws_ping(CURL *easy, const char *reason) {
    struct cws_data *priv;
    char *p = NULL;

    curl_easy_getinfo(easy, CURLINFO_PRIVATE, &p); /* checks for char* */
    if (!p) {
        ERR("not CWS (no CURLINFO_PRIVATE): %p", easy);
        return false;
    }
    priv = (struct cws_data *)p;

    return _cws_send(priv, CWS_OPCODE_PING,
                     reason, reason ? strlen(reason) : 0);
}

bool cws_pong(CURL *easy, const char *reason) {
    struct cws_data *priv;
    char *p = NULL;

    curl_easy_getinfo(easy, CURLINFO_PRIVATE, &p); /* checks for char* */
    if (!p) {
        ERR("not CWS (no CURLINFO_PRIVATE): %p", easy);
        return false;
    }
    priv = (struct cws_data *)p;

    return _cws_send(priv, CWS_OPCODE_PONG,
                     reason, reason ? strlen(reason) : 0);
}

static void _cws_cleanup(struct cws_data *priv) {
    CURL *easy;

    if (priv->dispatching > 0)
        return;

    if (!priv->deleted)
        return;

    easy = priv->easy;

    curl_slist_free_all(priv->headers);

    free(priv->websocket_protocols.requested);
    free(priv->websocket_protocols.received);
    free(priv->send.buffer);
    free(priv->recv.payload);
    free(priv);

    curl_easy_cleanup(easy);
}

bool cws_close(CURL *easy, enum cws_close_reason reason, const char *reason_text) {
    struct cws_data *priv;
    size_t len;
    uint16_t r;
    bool ret;
    char *p = NULL;

    curl_easy_getinfo(easy, CURLINFO_PRIVATE, &p); /* checks for char* */
    if (!p) {
        ERR("not CWS (no CURLINFO_PRIVATE): %p", easy);
        return false;
    }
    priv = (struct cws_data *)p;

    r = reason;
    if (!reason_text)
        reason_text = "";

    len = sizeof(uint16_t) + strlen(reason_text);
    p = malloc(len);
    memcpy(p, &r, sizeof(uint16_t));
    _cws_hton(p, sizeof(uint16_t));
    if (strlen(reason_text))
        memcpy(p + sizeof(uint16_t), reason_text, strlen(reason_text));

    ret = _cws_send(priv, CWS_OPCODE_CLOSE, p, len);
    free(p);
    priv->closed = true;
    return ret;
}

static void _cws_check_accept(struct cws_data *priv, const char *buffer, size_t len) {
    priv->accepted = false;

    if (len != sizeof(priv->accept_key) - 1) {
        ERR("expected %zd bytes, got %zd '%.*s'",
            sizeof(priv->accept_key) - 1, len, (int)len, buffer);
        return;
    }

    if (memcmp(priv->accept_key, buffer, len) != 0) {
        ERR("invalid accept key '%.*s', expected '%.*s'",
            (int)len, buffer, (int)len, priv->accept_key);
        return;
    }

    priv->accepted = true;
}

static void _cws_check_protocol(struct cws_data *priv, const char *buffer, size_t len) {
    if (priv->websocket_protocols.received)
        free(priv->websocket_protocols.received);

    priv->websocket_protocols.received = strndup(buffer, len);
}

static void _cws_check_upgrade(struct cws_data *priv, const char *buffer, size_t len) {
    priv->connection_websocket = false;

    if (len == strlen("websocket") &&
        strncasecmp(buffer, "websocket", len) != 0) {
        ERR("unexpected 'Upgrade: %.*s'. Expected 'Upgrade: websocket'",
            (int)len, buffer);
        return;
    }

    priv->connection_websocket = true;
}

static void _cws_check_connection(struct cws_data *priv, const char *buffer, size_t len) {
    priv->upgraded = false;

    if (len == strlen("upgrade") &&
        strncasecmp(buffer, "upgrade", len) != 0) {
        ERR("unexpected 'Connection: %.*s'. Expected 'Connection: upgrade'",
            (int)len, buffer);
        return;
    }

    priv->upgraded = true;
}

static size_t _cws_receive_header(const char *buffer, size_t count, size_t nitems, void *data) {
    struct cws_data *priv = data;
    size_t len = count * nitems;
    const struct header_checker {
        const char *prefix;
        void (*check)(struct cws_data *priv, const char *suffix, size_t suffixlen);
    } *itr, header_checkers[] = {
        {"Sec-WebSocket-Accept:", _cws_check_accept},
        {"Sec-WebSocket-Protocol:", _cws_check_protocol},
        {"Connection:", _cws_check_connection},
        {"Upgrade:", _cws_check_upgrade},
        {NULL, NULL}
    };

    if (len == 2 && memcmp(buffer, "\r\n", 2) == 0) {
        long status;

        curl_easy_getinfo(priv->easy, CURLINFO_HTTP_CONNECTCODE, &status);
        if (!priv->accepted) {
            if (priv->cbs.on_close) {
                priv->dispatching++;
                priv->cbs.on_close((void *)priv->cbs.data,
                                   priv->easy,
                                   CWS_CLOSE_REASON_SERVER_ERROR,
                                   "server didn't accept the websocket upgrade");
                priv->dispatching--;
                _cws_cleanup(priv);
            }
            return 0;
        } else {
            if (priv->cbs.on_connect) {
                priv->dispatching++;
                priv->cbs.on_connect((void *)priv->cbs.data,
                                     priv->easy,
                                     STR_OR_EMPTY(priv->websocket_protocols.received));
                priv->dispatching--;
                _cws_cleanup(priv);
            }
            return len;
        }
    }

    if (_cws_header_has_prefix(buffer, len, "HTTP/")) {
        priv->accepted = false;
        priv->upgraded = false;
        priv->connection_websocket = false;
        if (priv->websocket_protocols.received) {
            free(priv->websocket_protocols.received);
            priv->websocket_protocols.received = NULL;
        }
        return len;
    }

    for (itr = header_checkers; itr->prefix != NULL; itr++) {
        if (_cws_header_has_prefix(buffer, len, itr->prefix)) {
            size_t prefixlen = strlen(itr->prefix);
            size_t valuelen = len - prefixlen;
            const char *value = buffer + prefixlen;
            _cws_trim(&value, &valuelen);
            itr->check(priv, value, valuelen);
        }
    }

    return len;
}

static void _cws_dispatch(struct cws_data *priv) {
    switch (priv->recv.frame_header.opcode) {
    case CWS_OPCODE_CONTINUATION:
        return;

    case CWS_OPCODE_TEXT:
        if (priv->cbs.on_text)
            priv->cbs.on_text((void *)priv->cbs.data,
                              priv->easy,
                              (char *)priv->recv.payload,
                              priv->recv.used_len);
        return;

    case CWS_OPCODE_BINARY:
        if (priv->cbs.on_binary)
            priv->cbs.on_binary((void *)priv->cbs.data,
                                priv->easy,
                                priv->recv.payload,
                                priv->recv.used_len);
        return;

    case CWS_OPCODE_CLOSE:
        priv->closed = true;
        if (priv->cbs.on_close) {
            const char *text = "";
            uint16_t r = 0;
            if (priv->recv.used_len >= sizeof(uint16_t)) {
                memcpy(&r, priv->recv.payload, sizeof(uint16_t));
                _cws_ntoh(&r, sizeof(uint16_t));
                text = (const char *)priv->recv.payload + sizeof(uint16_t);
            }
            priv->cbs.on_close((void *)priv->cbs.data, priv->easy, r, text);
        }
        return;

    case CWS_OPCODE_PING:
        if (priv->cbs.on_ping) {
            priv->cbs.on_ping((void *)priv->cbs.data,
                              priv->easy,
                              STR_OR_EMPTY((char *)priv->recv.payload));
        } else {
            cws_pong(priv->easy, (char *)priv->recv.payload);
        }
        return;

    case CWS_OPCODE_PONG:
        if (priv->cbs.on_pong)
            priv->cbs.on_pong((void *)priv->cbs.data,
                              priv->easy,
                              STR_OR_EMPTY((char *)priv->recv.payload));
        return;

    default:
        ERR("unexpected WebSocket opcode: %#x", priv->recv.frame_header.opcode);
    }
}

static size_t _cws_receive_data(const char *buffer, size_t count, size_t nitems, void *data) {
    struct cws_data *priv = data;
    size_t len = count * nitems;
    size_t used = 0;

    /* start by needing a full frame header */
    if (priv->recv.needed == 0) {
        priv->recv.needed = sizeof(struct cws_frame_header);
        priv->recv.done = 0;
    }

    while (len > 0 && priv->recv.done < priv->recv.needed) {
        if (priv->recv.done < priv->recv.needed) {
            size_t todo = priv->recv.needed - priv->recv.done;
            if (todo > len)
                todo = len;
            memcpy(priv->recv.tmpbuf + priv->recv.done, buffer, todo);
            priv->recv.done += todo;
            used += todo;
            buffer += todo;
            len -= todo;
        }

        if (priv->recv.needed != priv->recv.done)
            continue;

        if (priv->recv.needed == sizeof(struct cws_frame_header)) {
            memcpy(&priv->recv.frame_header,
                   priv->recv.tmpbuf,
                   sizeof(struct cws_frame_header));

            if (priv->recv.frame_header.payload_len == 126) {
                priv->recv.needed += sizeof(uint16_t);
                continue;
            } else if (priv->recv.frame_header.payload_len == 127) {
                priv->recv.needed += sizeof(uint64_t);
                continue;
            } else
                priv->recv.frame_len = priv->recv.frame_header.payload_len;
        }

        if (priv->recv.needed == sizeof(struct cws_frame_header) + sizeof(uint16_t)) {
            uint16_t len;

            memcpy(&len,
                   priv->recv.tmpbuf + sizeof(struct cws_frame_header),
                   sizeof(len));
            _cws_ntoh(&len, sizeof(len));
            priv->recv.frame_len = len;
        } else if (priv->recv.needed == sizeof(struct cws_frame_header) + sizeof(uint64_t)) {
            uint64_t len;

            memcpy(&len, priv->recv.tmpbuf + sizeof(struct cws_frame_header),
                   sizeof(len));
            _cws_ntoh(&len, sizeof(len));
            priv->recv.frame_len = len;
        }

        if (priv->recv.frame_header.opcode != CWS_OPCODE_CONTINUATION) {
            priv->recv.total_len = 0;
            priv->recv.used_len = 0;
        }

        if (priv->recv.frame_len > 0) {
            void *tmp;

            tmp = realloc(priv->recv.payload,
                          priv->recv.total_len + priv->recv.frame_len + 1);
            if (!tmp) {
                ERR("could not allocate memory");
                return CURL_READFUNC_ABORT;
            }
            priv->recv.payload = tmp;
            priv->recv.total_len += priv->recv.frame_len;
        }
    }

    if (len == 0 && priv->recv.done < priv->recv.needed)
        return used;

    /* fill payload */
    while (len > 0 && priv->recv.used_len < priv->recv.total_len) {
        size_t todo = priv->recv.total_len - priv->recv.used_len;
        if (todo > len)
            todo = len;
        memcpy(priv->recv.payload + priv->recv.used_len, buffer, todo);
        priv->recv.used_len += todo;
        used += todo;
        buffer += todo;
        len -= todo;
    }
    if (priv->recv.total_len > 0)
        priv->recv.payload[priv->recv.used_len] = '\0';

    if (len == 0 && priv->recv.used_len < priv->recv.total_len)
        return used;

    /* finished? dispatch */
    if (priv->recv.frame_header.fin) {
        priv->dispatching++;

        _cws_dispatch(priv);

        free(priv->recv.payload);
        priv->recv.payload = NULL;
        priv->recv.done = 0;
        priv->recv.needed = 0;
        priv->recv.used_len = 0;
        priv->recv.total_len = 0;
        priv->dispatching--;
        _cws_cleanup(priv);
    }

    return used;
}

static size_t _cws_send_data(char *buffer, size_t count, size_t nitems, void *data) {
    struct cws_data *priv = data;
    size_t len = count * nitems;
    size_t todo = priv->send.len;

    if (todo == 0) {
        priv->pause_flags |= CURLPAUSE_SEND;
        return CURL_READFUNC_PAUSE;
    }
    if (todo > len)
        todo = len;

    memcpy(buffer, priv->send.buffer, todo);
    if (todo < priv->send.len) {
        /* optimization note: we could avoid memmove() by keeping a
         * priv->send.position, then we just increment that offset.
         *
         * on next _cws_write(), check if priv->send.position > 0 and
         * memmove() to make some space without realloc().
         */
        memmove(priv->send.buffer,
                priv->send.buffer + todo,
                todo - priv->send.len);
    } else {
        free(priv->send.buffer);
        priv->send.buffer = NULL;
    }

    priv->send.len -= todo;
    return todo;
}

static const char *_cws_fill_websocket_key(struct cws_data *priv, char key_header[static 44]) {
    uint8_t key[16];
    /* 24 bytes of base24 encoded key
     * + GUID 258EAFA5-E914-47DA-95CA-C5AB0DC85B11
     */
    char buf[60] = "01234567890123456789....258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
    uint8_t sha1hash[20];

    _cws_get_random(key, sizeof(key));

    _cws_encode_base64(key, sizeof(key), buf);
    memcpy(key_header + strlen("Sec-WebSocket-Key: "), buf, 24);

    _cws_sha1(buf, sizeof(buf), sha1hash);
    _cws_encode_base64(sha1hash, sizeof(sha1hash), priv->accept_key);
    priv->accept_key[sizeof(priv->accept_key) - 1] = '\0';

    return key_header;
}

CURL *cws_new(const char *url, const char *websocket_protocols, const struct cws_callbacks *callbacks) {
    CURL *easy;
    struct cws_data *priv;
    char key_header[] = "Sec-WebSocket-Key: 01234567890123456789....";
    char *tmp = NULL;

    if (!url)
        return NULL;

    easy = curl_easy_init();
    if (!easy)
        return NULL;

    priv = calloc(1, sizeof(struct cws_data));
    priv->easy = easy;
    curl_easy_setopt(easy, CURLOPT_PRIVATE, priv);
    curl_easy_setopt(easy, CURLOPT_HEADERFUNCTION, _cws_receive_header);
    curl_easy_setopt(easy, CURLOPT_HEADERDATA, priv);
    curl_easy_setopt(easy, CURLOPT_WRITEFUNCTION, _cws_receive_data);
    curl_easy_setopt(easy, CURLOPT_WRITEDATA, priv);
    curl_easy_setopt(easy, CURLOPT_READFUNCTION, _cws_send_data);
    curl_easy_setopt(easy, CURLOPT_READDATA, priv);

    if (callbacks)
        priv->cbs = *callbacks;

    /* curl doesn't support ws:// or wss:// scheme, rewrite to http/https */
    if (strncmp(url, "ws://", strlen("ws://")) == 0) {
        tmp = malloc(strlen(url) - strlen("ws://") + strlen("http://") + 1);
        memcpy(tmp, "http://", strlen("http://"));
        memcpy(tmp + strlen("http://"),
               url + strlen("ws://"),
               strlen(url) - strlen("ws://") + 1);
        url = tmp;
    } else if (strncmp(url, "wss://", strlen("wss://")) == 0) {
        tmp = malloc(strlen(url) - strlen("wss://") + strlen("https://") + 1);
        memcpy(tmp, "https://", strlen("https://"));
        memcpy(tmp + strlen("https://"),
               url + strlen("wss://"),
               strlen(url) - strlen("wss://") + 1);
        url = tmp;
    }
    curl_easy_setopt(easy, CURLOPT_URL, url);
    free(tmp);

    /*
     * BEGIN: work around CURL to get WebSocket:
     *
     * WebSocket must be HTTP/1.1 GET request where we must keep the
     * "send" part alive without any content-length and no chunked
     * encoding and the server answer is 101-upgrade.
     */
    curl_easy_setopt(easy, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_1_1);
    /* Use CURLOPT_UPLOAD=1 to force "send" even with a GET request,
     * however it will set HTTP request to PUT
     */
    curl_easy_setopt(easy, CURLOPT_UPLOAD, 1L);
    /*
     * Then we manually override the string sent to be "GET".
     */
    curl_easy_setopt(easy, CURLOPT_CUSTOMREQUEST, "GET");
    /*
     * CURLOPT_UPLOAD=1 with HTTP/1.1 implies:
     *     Expect: 100-continue
     * but we don't want that, rather 101. Then force: 101.
     */
    priv->headers = curl_slist_append(priv->headers, "Expect: 101");
    /*
     * CURLOPT_UPLOAD=1 without a size implies in:
     *     Transfer-Encoding: chunked
     * but we don't want that, rather unmodified (raw) bites as we're
     * doing the websockets framing ourselves. Force nothing.
     */
    priv->headers = curl_slist_append(priv->headers, "Transfer-Encoding:");
    /* END: work around CURL to get WebSocket. */

    /* regular mandatory WebSockets headers */
    priv->headers = curl_slist_append(priv->headers, "Connection: Upgrade");
    priv->headers = curl_slist_append(priv->headers, "Upgrade: websocket");
    priv->headers = curl_slist_append(priv->headers, "Sec-WebSocket-Version: 13");
    /* Sec-WebSocket-Key: <24-bytes-base64-of-random-key> */
    priv->headers = curl_slist_append(priv->headers, _cws_fill_websocket_key(priv, key_header));

    if (websocket_protocols) {
        char *tmp = malloc(strlen("Sec-WebSocket-Protocol: ") +
                           strlen(websocket_protocols) + 1);
        memcpy(tmp,
               "Sec-WebSocket-Protocol: ",
               strlen("Sec-WebSocket-Protocol: "));
        memcpy(tmp + strlen("Sec-WebSocket-Protocol: "),
               websocket_protocols,
               strlen(websocket_protocols) + 1);

        priv->headers = curl_slist_append(priv->headers, tmp);
        free(tmp);
        priv->websocket_protocols.requested = strdup(websocket_protocols);
    }

    curl_easy_setopt(easy, CURLOPT_HTTPHEADER, priv->headers);

    return easy;
}

void cws_free(CURL *easy) {
    struct cws_data *priv;
    char *p = NULL;

    curl_easy_getinfo(easy, CURLINFO_PRIVATE, &p); /* checks for char* */
    if (!p)
        return;
    priv = (struct cws_data *)p;

    priv->deleted = true;
    _cws_cleanup(priv);
}
