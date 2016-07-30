                              LIBLOGGER
                              =========

ABOUT
-----

liblogger will attempt to parse a given header file and produce a
source file that will provide exported functions, log the function
call, call the original function from specified library, then log the
function return. This may be used to log any dynamically loadable
library by means of $LD_PRELOAD environment variable.


CONCEPT
-------

Given a header "mylib.h":

    int func(void *ctx, struct param *params, int n_params);

we parse and produce the following library source (pseudo code) "log_mylib.c":

    #include <mylib.h>

    static void *_dl_handle = dlopen("libmylib.so", RTLD_LAZY);

    int func(void *ctx, struct param *params, int n_params) {
        static int (*_func)() = dlsym(_dl_handle, "func");
        int r;

        fprintf(logf, "LOG> func(%p, %p, %d)\n", ctx, params, n_params);

        r = _func(ctx, params, n_params);

        fprintf(logf, "LOG< func(%p, %p, %d) = %s\n", ctx, params, n_params, r);

        return r;
    }

of course this is a simplified version and the actual code have locks
to allow threaded libraries to be used, flush of file pointers and
actual logic to acquire symbols around dlopen()/dlsym().

Then users will compile it as a shared library (do not link with any
of mylib dependencies!):

    cc $(CFLAGS) log_mylib.c -o log_mylib.so -ldl -lpthread
    export LD_PRELOAD=$PWD/log_mylib.so
    run_mylib_program


It should output something like:

    LOG> func(0x123456, 0xaabb0000, 2)
    LOG< func(0x123456, 0xaabb0000, 2) = 0


CONFIGURATION
-------------

One may use a configuration file using Python's ConfigParser syntax
(ini-like), it can define the following sections and keys. Template
replacement is available with some keywods such as %(prefix)s that
expands to internal library prefix names (useful if you want to use
provided formatters and checkers):

    [global]

        ignore-tokens-regexp = string with regular expression
            if provided, this regular expression will filter out
            undesired tokens such as macros you want to remove
            (matches will be replaced with ""). Lines starting with
            "static " and compiler attributes declared with
            __attribute__(()) are always removed.
            Default: <empty>

        ignore-functions-regexp = string with regular expression
            if provided, this regular expression will filter out undesired
            functions by their names.
            Default: <empty>

        select-functions-regexp = string with regular expression
            if provided, this regular expression will filter out undesired
            functions by their names that do not match. It is applied
            after ignore-functions-regexp (double filtered).
            Default: <empty>

        overrides = filename1,filename2,...
            if provided, these files will be included before actual
            log wrapper calls so pieces of this code can be referred
            by the generated code. See function overrides below.
            Default: <empty>

        headers = filename1,filename2,...
            if provided, these files will be included before actual
            log wrapper calls or overrides. Likely you'll add files
            your parsed header depends on. If defined the source
            header will not be included automatically and you must do
            it explicitly (done to cope with libs such as dbus that
            prohibits including internal headers directly)
            Default: <empty>

        assume-safe-formatters = boolean
            if true, then all pointers are considered safe to be
            dereferenced. Use only if you know non-NULL pointers will
            not crash, strings (char*) are NULL terminated. DANGEROUS.
            Default: false


    [type-aliases]

        Allows hinting the processor that some types are just alias to
        some other type, just like typedef would do. This allow
        extending the known types others defined in included files or
        even fake typedefs did using cpp #define macros (that are
        ignored by our parser).

        <type> = <original-type>
            type will be considered as being original-type, just like:
            "typedef original-type type;" would do.


    [type-formatters]

        Allows user to extend the formatting of parameters and return
        values, enhancing the debug process.

        <type> = <formatter-function>
            type here is the original C type with spaces replaced with
            dashes, so "char *" becomes "char-*". These are catch-all
            that can be specified per function parameter or
            return. See function sections below.

            in order to be safe, formatters will not access pointer
            contents by default unless funct parameters or return are
            marked appropriately or "assume-safe-formatters = true" in
            "global" section. See safe-formatters and function
            sections below.

            formatter function is a C function provided by liblogger
            or by yourself with the overrides file included with the
            "overrides" key in "global" section. This function must
            have the signature:

               void fmt(FILE *output, /* where you should write */
                        const char *type, /* parameter type */
                        const char *name, /* parameter name or NULL if return */
                        <type> value)

             To avoid mixing names with original header file, all
             generated functions have %(prefix)s_log_fmt_<description>()
             naming scheme. Provided formatters:

                %(prefix)s_log_fmt_int
                %(prefix)s_log_fmt_uint
                %(prefix)s_log_fmt_hex_int
                %(prefix)s_log_fmt_errno
                %(prefix)s_log_fmt_octal_int
                %(prefix)s_log_fmt_char
                %(prefix)s_log_fmt_uchar
                %(prefix)s_log_fmt_hex_char
                %(prefix)s_log_fmt_octal_char
                %(prefix)s_log_fmt_short
                %(prefix)s_log_fmt_ushort
                %(prefix)s_log_fmt_hex_short
                %(prefix)s_log_fmt_long
                %(prefix)s_log_fmt_ulong
                %(prefix)s_log_fmt_hex_long
                %(prefix)s_log_fmt_long_long
                %(prefix)s_log_fmt_ulong_long
                %(prefix)s_log_fmt_hex_long_long
                %(prefix)s_log_fmt_bool
                %(prefix)s_log_fmt_string
                %(prefix)s_log_fmt_double
                %(prefix)s_log_fmt_pointer

             If we know the information about data types we can also
             generate custom formatters using the -F (--custom-formatters)
             command line options. It will generate for known enums,
             structs and unions based on declared methods. They will follow
             the pattern:

                %(prefix)s_log_fmt_custom_pointer_enum_%(name)s
                %(prefix)s_log_fmt_custom_value_enum_%(name)s
                %(prefix)s_log_fmt_custom_pointer_pointer_struct_%(name)s
                %(prefix)s_log_fmt_custom_pointer_struct_%(name)s
                %(prefix)s_log_fmt_custom_value_struct_%(name)s
                %(prefix)s_log_fmt_custom_pointer_pointer_union_%(name)s
                %(prefix)s_log_fmt_custom_pointer_union_%(name)s
                %(prefix)s_log_fmt_custom_value_union_%(name)s


    [safe-formatters]

        Allows user to define a single type formatter globally safe or
        unsafe.

        <type> = boolean
            if true, the type formatter is safe, otherwise it's not.
            Default: false or global/assume-safe-formatters


    [return-checkers]

        Allows user to check return value for errors.

        <type> = <checker-function>
            type here is the original C type with spaces replaced with
            dashes, so "char *" becomes "char-*".

            checker function is a C function provided by liblogger or
            by yourself with the overrides file included with the
            "overrides" key in "global" section. This function must
            have the signature:

               void fmt(FILE *output, /* where you should write */
                        const char *type, /* parameter type */
                        <type> value)

             To avoid mixing names with original header file, all
             generated functions have %(prefix)s_log_checker_<description>()
             naming scheme. Provided formatters:

                %(prefix)s_log_checker_null
                %(prefix)s_log_checker_non_null
                %(prefix)s_log_checker_zero
                %(prefix)s_log_checker_non_zero
                %(prefix)s_log_checker_false
                %(prefix)s_log_checker_true
                %(prefix)s_log_checker_errno (ignores values and uses errno)


    [func-%(function_name)s]

        Allows user to specify per function settings.

        override = function_name
            if provided, this function will be used instead of the
            original symbol. This function will receive the original
            symbol as the first parameter, followed by all parameters
            expected in the original function. Use this to do some
            ellaborated formatting or checks.
            Default: <empty>

        return-safe = boolean
            if true, the return is considered safe and if a non-NULL
            pointer its contents may be accessed.
            Default: false or global/assume-safe-formatters

        return-formatter = <formatter-function>
            if provided assigns a special formatter for function
            return value.
            Default: <empy> (depends on type)

        return-checker = <checker-function>
            if provided assigns a special checker for function
            return value.
            Default: <empy> (depends on type)

        return-default = value
            if provided overrides default return value (used on errors).
            Default: NULL or 0

        parameter-%(name)s-safe = boolean
            if true, the parameter is considered safe and if a non-NULL
            pointer its contents may be accessed.
            Default: false or global/assume-safe-formatters

        parameter-%(name)s-formatter = <formatter-function>
            if provided assigns a special formatter for function
            parameter value.
            Default: <empty> (depends on type)

        parameter-%(name)s-return = boolean
            if true then this parameter is a pointer that is used to
            return data (output parameter), so called "return
            parameter". This parameter will receive special formatting
            after the exit of the logged call ("LOG<") using a type
            dereference (*value) if available or if
            parameter-%(name)s-return-formatter is specified.
            Default: false

        parameter-%(name)s-return-formatter = <formatter-function>
            if parameter-%(name)s-return is true then this formatter
            will be used to log the returned value.
            Default: <empty> (depends on type)


Other than generation-time configuration, the resulting source file
will accept some CPP defines to toggle the behavior:

    %(prefix)s_USE_COLORS
        if defined ANSI colors will be used to aid debug.

    %(prefix)s_HAVE_THREADS
        if defined locks are used around debugging code so it's
        possible to print from concurrent threads without messing the
        output. Note that this won't lock around the actual function
        calls from logged library!

    %(prefix)s_LOGFILE="filename"
        if defined it will use the specified filename for logging
        instead of stderr.
