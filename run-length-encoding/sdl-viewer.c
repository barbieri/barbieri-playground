#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>

#include "sdl-viewer.h"

static void
wait_end(void)
{
        SDL_Event ev;

        while (SDL_WaitEvent(&ev)) {
                switch (ev.type) {
                case SDL_QUIT:
                        return;

                case SDL_KEYUP:
                        if (ev.key.keysym.sym == SDLK_q ||
                            ev.key.keysym.sym == SDLK_ESCAPE)
                                return;
                        break;
                default:
                        break;
                }
        }
}

static void
usage(const char *progname)
{
        fprintf(stderr,
                "Usage:\n"
                "\t%s <file.rle>\n"
                "\n",
                progname);
}

int
main(int argc, char *argv[])
{
        SDL_Surface *screen;
        const char *input;
        unsigned short w, h;
        rle_unit_type_t unit_type;
        rle_handle_t *handle;

        if (argc < 2) {
                usage(argv[0]);
                return -1;
        }

        input = argv[1];

        handle = rle_open(input);
        if (!handle) {
                fprintf(stderr, "Could not open file '%s'\n", input);
                return -1;
        }

        if (rle_parse_header(handle, &w, &h, &unit_type) != 0) {
                fprintf(stderr, "Could not load header\n");
                return -1;
        }

        if (SDL_Init(SDL_INIT_VIDEO) != 0) {
                fprintf(stderr, "Could not init SDL: %s\n", SDL_GetError());
                return -1;
        }

        screen = SDL_SetVideoMode(w, h, BPP, SDL_SWSURFACE);
        if (!screen) {
                fprintf(stderr, "Could not create screen %dx%dx%u: %s\n",
                        w, h, BPP, SDL_GetError());
                return -1;
        }
        SDL_FillRect(screen, NULL, 0xff00ff);

        if (rle_decode(handle, h, unit_type, screen->pixels,
                       screen->pitch) != 0) {
                fputs("Could not decode image.\n", stderr);
                return -1;
        }

        SDL_Flip(screen);
        wait_end();

        SDL_Quit();
        rle_close(handle);

        return 0;
}
