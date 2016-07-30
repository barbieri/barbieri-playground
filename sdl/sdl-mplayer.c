/**
 * Example on how to output Mplayer video on SDL windows.
 *
 * Mplayer and other players can output to some X11 Window, even if this
 * window belongs to another program/application/process.
 *
 * One X11 Window is not necessarily a top level window as shown by
 * window managers, rather it's a rectangular area where you can draw.
 * Often toolkits use windows to draw components, like a Button, so you
 * can use its Window ID and play video there.
 *
 * Using this feature with SDL may not work as expected, since a SDL
 * window is just one X11 window, so you cannot output to just part of
 * the window.
 *
 * In order to output to a subpart of a SDL screen, you need to create
 * a X11 window and attach it to SDL's X11 window, then you use its id
 * with the Mplayer -wid command line parameter.
 *
 * Basic X11/Xlib types:
 *  - Display: structure with connection to X11 server, we use SDL's.
 *  - Window: and integer that identifies an window on some display.
 *
 * Basic X11/Xlib programming:
 *  - X11 is a client/server protocol and Xlib is the C implementation.
 *  - Xlib is asynchronous, you should wait for events.
 *  - Xlib needs XFlush() to send events to server, otherwise it will stay
 *    on client.
 *
 * We get Display and Window from SDL_SysWMinfo, and to use Display without
 * messing up SDL, we need to lock it during operation.
 *
 *
 * BUILDING
 * ========
 *
 * gcc -lX11 $(sdl-config --libs --cflags) sdl-mplayer.c -o sdl-mplayer
 *
 *
 * REFERENCES
 * ==========
 *
 *  - http://tronche.com/gui/x/xlib/
 *  - http://users.actcom.co.il/~choo/lupg/tutorials/xlib-programming/xlib-programming.html
 *
 *
 * LICENSE
 * =======
 *
 * GNU-LGPL - GNU Lesser General Public License.
 *
 *
 * AUTHOR
 * ======
 *
 * Gustavo Sverzut Barbieri <barbieri@gmail.com>
 *
 */

#include <X11/Xlib.h>
#include <SDL/SDL.h>
#include <SDL/SDL_syswm.h>

#include <stdio.h>

Window
create_x11_subwindow (Display *dpy,
                      Window parent,
                      int x,
                      int y,
                      int width,
                      int height)
{
  Window win;
  int black;

  if (!dpy)
    return 0;

  black = BlackPixel (dpy, DefaultScreen (dpy));
  win = XCreateSimpleWindow (dpy, parent, x, y, width, height,
                             0, black, black);

  if (!win)
    return 0;

  if (!XSelectInput (dpy, win, StructureNotifyMask))
    return 0;

  if (!XMapWindow (dpy, win))
    return 0;

  while (1) {
    XEvent e;
    XNextEvent (dpy, &e);
    if (e.type == MapNotify && e.xmap.window == win)
      break;
  }

  XSelectInput (dpy, win, NoEventMask);

  return win;
}

int
init_sdl (void)
{
  if (SDL_Init (SDL_INIT_VIDEO) < 0) {
    fprintf (stderr, "Failed to init SDL: %s\n", SDL_GetError ());
    return 0;
  }
  atexit (SDL_Quit);

  if (SDL_SetVideoMode (800, 600, 0, SDL_ASYNCBLIT | SDL_HWSURFACE) == NULL) {
    fprintf (stderr, "Failed to init Video: %s\n", SDL_GetError ());
    return 0;
  }

  return 1;
}

SDL_SysWMinfo
get_sdl_wm_info (void)
{
  SDL_SysWMinfo sdl_info;

  memset (&sdl_info, 0, sizeof (sdl_info));

  SDL_VERSION (&sdl_info.version);
  if (SDL_GetWMInfo (&sdl_info) <= 0 ||
      sdl_info.subsystem != SDL_SYSWM_X11) {
    fprintf (stderr, "This is not X11\n");

    memset (&sdl_info, 0, sizeof (sdl_info));
    return sdl_info;
  }

  return sdl_info;
}

Window
create_sdl_x11_subwindow (int x,
                          int y,
                          int width,
                          int height)
{
  SDL_SysWMinfo sdl_info;
  Window play_win;

  sdl_info = get_sdl_wm_info ();
  if (!sdl_info.version.major)
    return 0;

  sdl_info.info.x11.lock_func ();

  play_win = create_x11_subwindow (sdl_info.info.x11.display,
                                   sdl_info.info.x11.window,
                                   x, y, width, height);

  sdl_info.info.x11.unlock_func ();

  return play_win;
}

void
main_loop (FILE *mplayer_fp)
{
  SDL_Surface *screen;
  Uint32 color;
  unsigned c_shift, run;

  fprintf (stderr, "Type 'q' or Escape to exit\n");

  screen = SDL_GetVideoSurface ();
  run = 1;
  color = 0x000000;
  c_shift = 1;
  while (run) {
    SDL_Event event;

    while (SDL_PollEvent (&event)) {
      switch (event.type) {
      case SDL_QUIT:
        fprintf (mplayer_fp, "quit\n");
        run = 0;
        break;

      case SDL_KEYDOWN:
        switch (event.key.keysym.sym) {
        case SDLK_q:
        case SDLK_ESCAPE:
          fprintf (mplayer_fp, "quit\n");
          run = 0;
          break;
        default:
          break;
        }
        break;

      default:
        break;
      }
    }

    SDL_FillRect (screen, NULL, color);
    SDL_Flip (screen);
    color |= 0x1 << c_shift;
    c_shift ++;

    if (c_shift >= 32) {
      c_shift = 0;
      color = 0;
    }

    SDL_Delay (20);
  }
}

void
create_mplayer (const char *filename,
                Window win,
                FILE **mplayer_fp)
{
  char cmdline[1024];

  snprintf (cmdline, 1024, "mplayer -slave -wid 0x%lx %s", win, filename);

  *mplayer_fp = popen (cmdline, "w");
}

int
main(int argc,
     char *argv[])
{
  Window play_win;
  FILE *mplayer_fp;

  if (argc < 2) {
    fprintf (stderr, "Usage:\n\t%s <uri>\n\n", argv[0]);
    return -1;
  }

  if (!init_sdl ())
    return -1;

  play_win = create_sdl_x11_subwindow (20, 20, 760, 560);
  if (!play_win) {
    fprintf (stderr, "Cannot create X11 window\n");
    return -1;
  }

  mplayer_fp = NULL;
  create_mplayer (argv[1], play_win, &mplayer_fp);
  main_loop (mplayer_fp);
  pclose (mplayer_fp);

  return 0;
}

