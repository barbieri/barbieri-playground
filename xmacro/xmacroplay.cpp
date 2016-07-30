/*****************************************************************************
 *
 * xmacroplay - a utility for playing X mouse and key events.
 * Portions Copyright (C) 2000 Gabor Keresztfalvi <keresztg@mail.com>
 *
 * The recorded events are read from the standard input.
 *
 * This program is heavily based on
 * xremote (http://infa.abo.fi/~chakie/xremote/) which is:
 * Copyright (C) 2000 Jan Ekholm <chakie@infa.abo.fi>
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
 ****************************************************************************/

/*****************************************************************************
 * Includes
 ****************************************************************************/
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <ctype.h>
#include <X11/Xlibint.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/cursorfont.h>
#include <X11/keysymdef.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>

#include "chartbl.h"
/*****************************************************************************
 * What iostream do we have?
 ****************************************************************************/
#include <iostream>
#include <sstream>
#include <fstream>
#include <iomanip>

#define PROG "xmacroplay"

using namespace std;

/****************************************************************************/
/*! Prints the usage, i.e. how the program is used. Exits the application with
  the passed exit-code.

  \arg const int ExitCode - the exitcode to use for exiting.
*/
/****************************************************************************/
static void usage (const int exitCode) {

    // print the usage
    cerr << PROG << " " << VERSION << endl;
    cerr << "Usage: " << PROG << " [options]" << endl;
    cerr << "Options: " << endl
         << "  -v          show version. " << endl
         << "  -h          this help. " << endl << endl;

    // we're done
    exit ( exitCode );
}


/****************************************************************************/
/*! Prints the version of the application and exits.
 */
/****************************************************************************/
static void version () {

    // print the version
    cerr << PROG << " " << VERSION << endl;

    // we're done
    exit ( EXIT_SUCCESS );
}


/****************************************************************************/
/*! Parses the commandline and stores all data in globals (shudder). Exits
  the application with a failed exitcode if a parameter is illegal.

  \arg int argc - number of commandline arguments.
  \arg char * argv[] - vector of the commandline argument strings.
*/
/****************************************************************************/
static void parseCommandLine (int argc, char * argv[]) {

    int Index = 1;

    // loop through all arguments except the last, which is assumed to be the
    // name of the display
    while ( Index < argc ) {

        // is this '-v'?
        if ( strcmp (argv[Index], "-v" ) == 0 ) {
            // yep, show version and exit
            version ();
        }

        // is this '-h'?
        if ( strcmp (argv[Index], "-h" ) == 0 ) {
            // yep, show usage and exit
            usage ( EXIT_SUCCESS );
        }

        else {
            // we got this far, the parameter is no good...
            cerr << "Invalid parameter '" << argv[Index] << "'." << endl;
            usage ( EXIT_FAILURE );
        }

        // next value
        Index++;
    }
}

/****************************************************************************/
/*! Connects to the desired display. Returns the \c Display or \c 0 if
  no display could be obtained.

  \arg const char * DisplayName - name of the remote display.
*/
/****************************************************************************/
Display * remoteDisplay () {

    int Event, Error;
    int Major, Minor;
    const char * DisplayName = getenv ( "DISPLAY" );

    // open the display
    Display * D = XOpenDisplay ( DisplayName );

    // did we get it?
    if ( ! D ) {
        // nope, so show error and abort
        cerr << PROG << ": could not open display \"" << XDisplayName ( DisplayName )
             << "\", aborting." << endl;
        exit ( EXIT_FAILURE );
    }

    // does the remote display have the Xtest-extension?
    if ( ! XTestQueryExtension (D, &Event, &Error, &Major, &Minor ) ) {
        // nope, extension not supported
        cerr << PROG << ": XTest extension not supported on server \""
             << DisplayString(D) << "\"" << endl;

        // close the display and go away
        XCloseDisplay ( D );
        exit ( EXIT_FAILURE );
    }

    // print some information
    cerr << "XTest for server \"" << DisplayString(D) << "\" is version "
         << Major << "." << Minor << "." << endl << endl;;

    // execute requests even if server is grabbed
    XTestGrabControl ( D, True );

    // sync the server
    XSync ( D,True );

    // return the display
    return D;
}

/****************************************************************************/
/*! Sends a \a character to the remote display \a RemoteDpy. The character is
  converted to a \c KeySym based on a character table and then reconverted to
  a \c KeyCode on the remote display. Seems to work quite ok, apart from
  something weird with the Alt key.

  \arg Display * RemoteDpy - used display.
  \arg char c - character to send.
*/
/****************************************************************************/
static void sendChar(Display *RemoteDpy, char c)
{
    KeySym ks, sks, *kss, ksl, ksu;
    KeyCode kc, skc;
    int syms;
#ifdef DEBUG
    int i;
#endif

    sks=XK_Shift_L;

    ks=XStringToKeysym(chartbl[0][(unsigned char)c]);
    if ( ( kc = XKeysymToKeycode ( RemoteDpy, ks ) ) == 0 )
    {
        cerr << "No keycode on remote display found for char: " << c << endl;
        return;
    }
    if ( ( skc = XKeysymToKeycode ( RemoteDpy, sks ) ) == 0 )
    {
        cerr << "No keycode on remote display found for XK_Shift_L!" << endl;
        return;
    }

    kss=XGetKeyboardMapping(RemoteDpy, kc, 1, &syms);
    if (!kss)
    {
        cerr << "XGetKeyboardMapping failed on the remote display (keycode: " << kc << ")" << endl;
        return;
    }
    for (; syms && (!kss[syms-1]); syms--);
    if (!syms)
    {
        cerr << "XGetKeyboardMapping failed on the remote display (no syms) (keycode: " << kc << ")" << endl;
        XFree(kss);
        return;
    }
    XConvertCase(ks,&ksl,&ksu);
#ifdef DEBUG
    cout << "kss: ";
    for (i=0; i<syms; i++) cout << kss[i] << " ";
    cout << "(" << ks << " l: " << ksl << "  h: " << ksu << ")" << endl;
#endif
    if (ks==kss[0] && (ks==ksl && ks==ksu)) sks=NoSymbol;
    if (ks==ksl && ks!=ksu) sks=NoSymbol;
    if (sks!=NoSymbol) XTestFakeKeyEvent ( RemoteDpy, skc, True, CurrentTime );
    XTestFakeKeyEvent ( RemoteDpy, kc, True, CurrentTime );
    XFlush ( RemoteDpy );
    XTestFakeKeyEvent ( RemoteDpy, kc, False, CurrentTime );
    if (sks!=NoSymbol) XTestFakeKeyEvent ( RemoteDpy, skc, False, CurrentTime );
    XFlush ( RemoteDpy );
    XFree(kss);
}

static void doSleep ( double seconds ) {
    struct timespec ts, remaining;

    ts.tv_sec = (int)seconds;
    ts.tv_nsec = (seconds - ts.tv_sec) * 1000000000;

    remaining = ts;
    while ( remaining.tv_sec > 0 || remaining.tv_nsec > 0 ) {
        if ( nanosleep ( &ts, &remaining ) == 0 ) {
            break;
        } else {
            if ( errno != EINTR ) {
                const char *errmsg = strerror(errno);
                cerr << "Could not sleep " << seconds << ": " << errmsg << endl;
                exit ( EXIT_FAILURE );
            }
            ts = remaining;
        }
    }
}

static string replaceTemplate( const char *templ )
{
    const char *itr;
    ostringstream s;
    static int count = 1;

    for ( itr = templ; *itr != '\0'; ) {
        if ( *itr != '%' ) {
            s << *itr;
            itr++;
        } else {
            itr++;
            switch ( *itr ) {
            case '%': s << '%'; break;
            case 'n': s << count; count++; break;
            case 'T':
            case 'D':
            case 't':
            {
                char tmp[128];
                char fmt[32];
                const struct tm * tm;
                time_t t;

                if ( *itr == 'T' ) strcpy( fmt, "'%X'" );
                else if ( *itr == 'D' ) strcpy ( fmt, "'%x'" );
                else if ( *itr == 't' ) strcpy ( fmt, "'%Y%m%d'" );

                t = time( NULL );
                tm = localtime( &t );

                if ( strftime( tmp, sizeof(tmp), fmt, tm ) < sizeof(tmp) )
                    s << tmp;
                else {
                    cerr << "Could not format time %" << *itr << endl;
                    return "";
                }
            }
            break;

            default:
                cerr << "Invalid sequence %" << *itr << endl;
                return "";
            }
            itr++;
        }
    }

    return s.str();
}

static int execCommand( const char *templ )
{
    string cmd = replaceTemplate( templ );
    int ret;

    if ( cmd.empty() )
        return EXIT_FAILURE;

    cout << "Exec " << cmd << endl;

    ret = system( cmd.c_str() );
    if ( ret < 0 ) {
        cerr << "Failed to execute: '" << cmd << "'. Error: " <<
            strerror(errno) << endl;
        return EXIT_FAILURE;
    } else if ( ret != 0 ) {
        cerr << "Command returned error '" << cmd << "'. Retval=" <<
            ret << endl;
        return ret;
    }

    return EXIT_SUCCESS;
}

static bool screenShot( Display *dpy, int screen, int x, int y, int w, int h, const char *templ )
{
    string file = replaceTemplate( templ );
    XImage *img;
    Drawable drawable = DefaultRootWindow( dpy );
    Visual *visual;
    Window swin;
    int sx, sy;
    unsigned int sw, sh, sborder, sdepth;

    if ( file.empty() )
        return false;

    XFlush( dpy );

    if (!XGetGeometry( dpy, drawable, &swin,
                       &sx, &sy, &sw, &sh, &sborder, &sdepth ) ) {
        cerr << "Screenshot: Failed to query window size." << endl;
        return false;
    }

    if ( w <= 0 || (unsigned)w > sw ) w = sw;
    if ( h <= 0 || (unsigned)h > sh ) h = sh;

    if ( x < sx )
        x = sx;
    else if ( (unsigned)x + w > sw )
        w = sw - x;

    if ( y < sy )
        y = sy;
    else if ( (unsigned)y + h > sh )
        h = sh - y;

    if ( w <= 0 || h <= 0 ) {
        cerr << "Invalid screenshot geomery: " <<
            x << "," << y << " " << w << "x" << h << endl;
        return false;
    }

    cout << "Screenshot " << x << " " << y <<
        " " << w << " " << h << " " << file << endl;

    if ( sdepth != 24 && sdepth != 32 ) {
        cerr << "Invalid bit depth:" << sdepth << endl;
        return false;
    }

    visual = DefaultVisual( dpy, screen );
    if ( !visual ) {
        cerr << "Failed to get X11 visual" << endl;
        return false;
    }

    if ( visual->c_class != TrueColor && visual->c_class != DirectColor ) {
        cerr << "Unsupported visual class " << visual->c_class <<
            ". Expected TrueColor or DirectColor." << endl;
        return false;
    }

    if ( visual->red_mask != 0xff0000 ||
         visual->green_mask != 0x00ff00 ||
         visual->blue_mask != 0x0000ff ) {
        cerr << "Unsupported Masks Red:" << visual->red_mask <<
            " Green:" << visual->green_mask <<
            " Blue:" << visual->blue_mask << endl;
        return false;
    }

    img = XGetImage( dpy, drawable, x, y, w, h, AllPlanes, ZPixmap );
    if ( !img ) {
        cerr << "Failed to create capture image" << endl;
        return false;
    }

    if ( img->bits_per_pixel != 32 ) {
        cerr << "Don't know how to handle " << img->bits_per_pixel <<
            " bits per pixel!" << endl;
        XDestroyImage( img );
        return false;
    }

    ofstream outfile( file.c_str(), ofstream::binary );
    char buf[128];
    int len = snprintf(buf, sizeof(buf), "P6\n%d %d\n255\n", w, h);
    outfile.write(buf, len);

    if ( img->bits_per_pixel == 32 ) {
        char *itr, *itrEnd;

        itr = img->data;
        itrEnd = itr + w * h * 4;

        if ( img->byte_order == MSBFirst ) {
            for ( ; itr < itrEnd; itr += 4 )
                outfile.write(itr + 1, 3);
        } else {
            for ( ; itr < itrEnd; itr += 4 ) {
                char data[3] = {itr[2], itr[1], itr[0]};
                outfile.write(data, 3);
            }
        }
    }

    outfile.close();
    XDestroyImage( img );

    return true;
}

static bool extractTag(const string &str, string &tag, string &payload)
{
    const string whitespace = " \t\n\r";
    size_t first, middle, last, length;

    first = str.find_first_not_of(whitespace);
    if (first == string::npos)
        return false;

    middle = str.find_first_of(whitespace, first + 1);
    length = middle - first;
    tag = str.substr(first, length);

    middle = str.find_first_not_of(whitespace, middle + 1);
    last = str.find_last_not_of(whitespace);
    length = last - middle + 1;
    payload = str.substr(middle, length);

    return true;
}

/****************************************************************************/
/*! Main event-loop of the application. Loops until a key with the keycode
  \a QuitKey is pressed. Sends all mouse- and key-events to the remote
  display.

  \arg Display * RemoteDpy - used display.
  \arg int RemoteScreen - the used screen.
*/
/****************************************************************************/
static int eventLoop (Display * RemoteDpy, int RemoteScreen) {
    while ( !cin.eof() ) {
        string line, tag, payload;

        getline(cin, line);
        if ( !extractTag(line, tag, payload) )
            continue;

        if (tag[0] == '#')
        {
            cout << line << endl;
            continue;
        } else if (!strcasecmp("Delay", tag.c_str()))
        {
            double Delay = atof(payload.c_str());
            cout << "Delay " << Delay << endl;
            doSleep ( Delay );
        }
        else if (!strcasecmp("ButtonPress", tag.c_str()))
        {
            unsigned int Button = atoi(payload.c_str());
            cout << "ButtonPress " << Button << endl;
            XTestFakeButtonEvent ( RemoteDpy, Button, True, CurrentTime );
        }
        else if (!strcasecmp("ButtonRelease", tag.c_str()))
        {
            unsigned int Button = atoi(payload.c_str());
            cout << "ButtonRelease " << Button << endl;
            XTestFakeButtonEvent ( RemoteDpy, Button, False, CurrentTime );
        }
        else if (!strcasecmp("MotionNotify", tag.c_str()))
        {
            int x, y;
            if ( sscanf(payload.c_str(), "%d %d", &x, &y) != 2 ) {
                cerr << "Invalid MotionNotify parameters:" << payload << endl;
                continue;
            }
            cout << "MotionNotify " << x << " " << y << endl;
            XTestFakeMotionEvent ( RemoteDpy, RemoteScreen , x, y, CurrentTime );
        }
        else if (!strcasecmp("KeyCodePress", tag.c_str()))
        {
            KeyCode kc = atoi(payload.c_str());
            cout << "KeyPress " << kc << endl;
            XTestFakeKeyEvent ( RemoteDpy, kc, True, CurrentTime );
        }
        else if (!strcasecmp("KeyCodeRelease", tag.c_str()))
        {
            KeyCode kc = atoi(payload.c_str());
            cout << "KeyRelease " << kc << endl;
            XTestFakeKeyEvent ( RemoteDpy, kc, False, CurrentTime );
        }
        else if (!strcasecmp("KeySym", tag.c_str()))
        {
            KeySym ks = atoi(payload.c_str());
            KeyCode kc;
            cout << "KeySym " << ks << endl;
            if ( ( kc = XKeysymToKeycode ( RemoteDpy, ks ) ) == 0 )
            {
                cerr << "No keycode on remote display found for keysym: " << ks << endl;
                continue;
            }
            XTestFakeKeyEvent ( RemoteDpy, kc, True, CurrentTime );
            XFlush ( RemoteDpy );
            XTestFakeKeyEvent ( RemoteDpy, kc, False, CurrentTime );
        }
        else if (!strcasecmp("KeySymPress", tag.c_str()))
        {
            KeySym ks = atoi(payload.c_str());
            KeyCode kc;
            cout << "KeySymPress " << ks << endl;
            if ( ( kc = XKeysymToKeycode ( RemoteDpy, ks ) ) == 0 )
            {
                cerr << "No keycode on remote display found for keysym: " << ks << endl;
                continue;
            }
            XTestFakeKeyEvent ( RemoteDpy, kc, True, CurrentTime );
        }
        else if (!strcasecmp("KeySymRelease", tag.c_str()))
        {
            KeySym ks = atoi(payload.c_str());
            KeyCode kc;
            cout << "KeySymRelease " << ks << endl;
            if ( ( kc = XKeysymToKeycode ( RemoteDpy, ks ) ) == 0 )
            {
                cerr << "No keycode on remote display found for keysym: " << ks << endl;
                continue;
            }
            XTestFakeKeyEvent ( RemoteDpy, kc, False, CurrentTime );
        }
        else if (!strcasecmp("KeyStr", tag.c_str()))
        {
            KeySym ks;
            KeyCode kc;
            cout << "KeyStr " << payload << endl;
            ks = XStringToKeysym(payload.c_str());
            if ( ( kc = XKeysymToKeycode ( RemoteDpy, ks ) ) == 0 )
            {
                cerr << "No keycode on remote display found for '" << payload << "': " << ks << endl;
                continue;
            }
            XTestFakeKeyEvent ( RemoteDpy, kc, True, CurrentTime );
            XFlush ( RemoteDpy );
            XTestFakeKeyEvent ( RemoteDpy, kc, False, CurrentTime );
        }
        else if (!strcasecmp("KeyStrPress", tag.c_str()))
        {
            KeySym ks;
            KeyCode kc;
            cout << "KeyStrPress " << payload << endl;
            ks=XStringToKeysym(payload.c_str());
            if ( ( kc = XKeysymToKeycode ( RemoteDpy, ks ) ) == 0 )
            {
                cerr << "No keycode on remote display found for '" << payload << "': " << ks << endl;
                continue;
            }
            XTestFakeKeyEvent ( RemoteDpy, kc, True, CurrentTime );
        }
        else if (!strcasecmp("KeyStrRelease", tag.c_str()))
        {
            KeySym ks;
            KeyCode kc;
            cout << "KeyStrRelease " << payload << endl;
            ks=XStringToKeysym(payload.c_str());
            if ( ( kc = XKeysymToKeycode ( RemoteDpy, ks ) ) == 0 )
            {
                cerr << "No keycode on remote display found for '" << payload << "': " << ks << endl;
                continue;
            }
            XTestFakeKeyEvent ( RemoteDpy, kc, False, CurrentTime );
        }
        else if (!strcasecmp("String", tag.c_str())) {
            cout << "String " << payload << endl;
            for (string::iterator it = payload.begin(); it != payload.end(); ++it)
                sendChar(RemoteDpy, *it);
        } else if (!strcasecmp("Exec", tag.c_str())) {
            int ret = execCommand( payload.c_str() );
            if ( ret != EXIT_SUCCESS )
                return ret;
        } else if (!strcasecmp("Screenshot", tag.c_str())) {
            int sx, sy, sw, sh;
            char name[4096];

            if (sscanf(payload.c_str(), "%d %d %d %d %4096s",
                       &sx, &sy, &sw, &sh, name) != 5) {
                cerr << "Invalid Screenshot parameters:" << payload << endl;
                continue;
            }
            if ( !screenShot( RemoteDpy, RemoteScreen, sx, sy, sw, sh, name) )
                return EXIT_FAILURE;
        } else if (!tag.empty()) {
            cerr << "Unknown line: " << line << endl;
        }

        // sync the remote server
        XFlush ( RemoteDpy );
    }

    return 0;
}


/****************************************************************************/
/*! Main function of the application. It expects no commandline arguments.

  \arg int argc - number of commandline arguments.
  \arg char * argv[] - vector of the commandline argument strings.
*/
/****************************************************************************/
int main (int argc, char * argv[]) {
    int exitCode;

    // parse commandline arguments
    parseCommandLine ( argc, argv );

    // open the remote display or abort
    Display * RemoteDpy = remoteDisplay ();

    // get the screens too
    int RemoteScreen = DefaultScreen ( RemoteDpy );

    XTestDiscard ( RemoteDpy );

    // start the main event loop
    exitCode = eventLoop ( RemoteDpy, RemoteScreen );

    // discard and even flush all events on the remote display
    XTestDiscard ( RemoteDpy );
    XFlush ( RemoteDpy );

    // we're done with the display
    XCloseDisplay ( RemoteDpy );

    cerr << PROG << ": pointer and keyboard released. " << endl;

    // go away
    exit ( exitCode );
}
