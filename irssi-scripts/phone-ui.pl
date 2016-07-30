use Irssi;
use strict;
use FileHandle;

use vars qw($VERSION %IRSSI);

$VERSION = "0.1";
%IRSSI = (
    authors     => 'Gustavo Sverzut Barbieri <barbieri@profusion.mobi>',
    name        => 'phone-ui',
    description => 'toggles phone-friendly user interface',
    license     => 'GPL v2',
    url         => 'none',
);

my $last_awl_hide_data = Irssi::settings_get_int("awl_hide_data");
my $phone_ui_mode = 0;

sub phone_ui_hilight_show {
    my $win = Irssi::window_find_name("hilight");
    if (!$win) {
        return;
    }
    my $num = $win->{"refnum"};
    Irssi::command("window goto 1");
    Irssi::command("window stick $num off");
    Irssi::command("window show $num");
    Irssi::command("window size 6");
    Irssi::command("window stick $num on");
    Irssi::command("window goto 1");
}

sub phone_ui_hilight_hide {
    my $win = Irssi::window_find_name("hilight");
    if (!$win) {
        return;
    }
    my $num = $win->{"refnum"};
    Irssi::command("window stick $num off");
    Irssi::command("window hide $num");
}

sub phone_ui_awl_less {
    $last_awl_hide_data = Irssi::settings_get_int("awl_hide_data");
    Irssi::command("set awl_hide_data 2");
}

sub phone_ui_awl_restore {
    Irssi::command("set awl_hide_data $last_awl_hide_data");
}

sub phone_ui_act_show {
    Irssi::command("statusbar window add -after lag -priority 10 act");
}

sub phone_ui_act_hide {
    Irssi::command("statusbar window remove act");
}

sub phone_ui_mark_all_read {
    foreach my $w (Irssi::windows()) {
        if ($w->{"data_level"} < 3) {
            $w->print("%K*** %Wactivated automatically by phone-ui %K***", MSGLEVEL_NEVER);
            $w->set_active();
        }
    }
}

sub phone_ui_enter {
    if ($phone_ui_mode) {
        return;
    }
    $phone_ui_mode = 1;

    phone_ui_hilight_hide();
    phone_ui_mark_all_read();
    phone_ui_awl_less();
    phone_ui_act_show();
}

sub phone_ui_exit {
    if (!$phone_ui_mode) {
        return;
    }
    $phone_ui_mode = 0;

    phone_ui_hilight_show();
    phone_ui_awl_restore();
    phone_ui_act_hide();
}

Irssi::command_bind('phone_ui_enter', 'phone_ui_enter');
Irssi::command_bind('phone_ui_exit', 'phone_ui_exit');

sub unload ($$$) {
    phone_ui_exit();
}
Irssi::signal_add_first('command script unload' => 'unload');
