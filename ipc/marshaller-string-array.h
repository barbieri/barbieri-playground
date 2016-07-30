#ifndef __MARSHALLER_STRING_ARRAY_H__
#define __MARSHALLER_STRING_ARRAY_H__

char *marshal_string_array(int *buflen, char *buf, int *reqlen, int argc, const char * const *argv);
char **unmarshal_string_array(char *buf, int *argc);

#endif /* __MARSHALLER_STRING_ARRAY_H__ */
