#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:        byfly.py
# Purpose:
#
# Author:      Александр
#
# Created:     28.10.2011
# Copyright:   (c) Александр -2011
# -------------------------------------------------------------------------------
# To install MatPlotLib in Debian/Ubuntu Linux run
# > sudo apt-get install python-matplotlib
from __future__ import unicode_literals, absolute_import
import logging
import optparse
import atexit
import byflyuser
import sys
import sqlite3 as db
import getpass
import os.path

__VERSION__ = '3.0'
__FIGURE_FORMATS__ = ['png', 'pdf', 'svg', 'eps', 'ps']

_DEFAULT_DATABASE_FILENAME = 'users.db'
HAS_MATPLOT = False

logger = logging.getLogger(__name__)
plotinfo = None


def pause():
    """Show 'press any key'"""
    raw_input("Press <Enter> to close")


def import_plot():
    global plotinfo
    global HAS_MATPLOT
    if 'plotinfo' not in sys.modules:
        try:

            print("Enabling plotting. Wait a few seconds...")
            import plotinfo

            print("All OK. Plotting enabled")
            HAS_MATPLOT = True
        except Exception:
            print ("Warning: MatPlotlib not installed - Plotting not working.")


def pass_from_db(login, db_filename, opt):
    """Get password from database file. Return password or None """
    import database

    try:
        db_manager = database.DBManager(database.Table(db_filename))
        res = db_manager.get_password(login)
        if res:
            opt.login = res[0]
            return res[1]
        else:
            return None
    except Exception as e:
        print(e)
        return None


def check_image_filename(option, opt_str, value, parser):
    """Check image format"""
    if not value:
        raise optparse.OptionValueError("option -s: Can't use without parameter")
    if not parser.values.graph:
        raise optparse.OptionValueError("option -s: Can't use without -g")
    if [value for ext in __FIGURE_FORMATS__ if value.endswith(ext)]:
        parser.values.imagefilename = value
    else:
        raise optparse.OptionValueError("option -s: Not correct file format. Use formats: %s" % __FIGURE_FORMATS__)


class UI(object):
    pass

class Program(object):
    def ui(self, opt, showgraph=None):
        """
        Output all information. If showgraph=='always' graph show and save to file
        """
        if opt.graph:
            import_plot()
        user = byflyuser.ByFlyUser(opt.login, opt.password)
        if user.login():
            if opt.quiet:
                user.print_info(True)
                return
            user.print_info()
            user.print_additional_info()
            if opt.graph and HAS_MATPLOT:
                plt = plotinfo.Plotter()
                if opt.imagefilename:
                    fname = opt.imagefilename
                    show = False
                else:
                    show = True
                    fname = None
                if showgraph == 'always':
                    show = True
                if opt.graph == 'time':
                    plt.plot_time_allocation(user.get_log(previous_period=opt.previous_period), title=user.info, show=show, fname=fname)
                elif opt.graph == 'traf':
                    plt.plot_traf_allocation(user.get_log(previous_period=opt.previous_period), title=user.info, show=show, fname=fname)
        else:
            print("Can't Log: " + user.get_last_error())

    def setup_cmd_parser(self):
        p = optparse.OptionParser(description='Проверка баланса ByFly', prog='ByFlyPy',
                                  version='%%prog %s' % __VERSION__)
        p.add_option("-i", action="store_true", dest="interactive", help="enable interactive mode")
        p.add_option("-l", "--login", action="store", type="string", dest="login", help='login')
        p.add_option("--list", type="string", dest="check_list", metavar='<filename>',
                     help="check accounts in file. Each line of file must be login:password")
        p.add_option("-p", "--p", action="store", type="string", dest="password", help='password')
        p.add_option("-g", "--graph", action="store", dest="graph", type='choice',
                     help="plot a graph. Parameters MUST BE traf or time ", choices=['traf', 'time'])
        p.add_option("--previous", action="store_true", dest="previous_period", help='get statistic for previous month', default=False)
        p.add_option("-s", "--save", action='callback', help='save graph to file', callback=check_image_filename,
                     type='string')
        p.add_option("-n", "--nologo", action='store_true', dest='nologo', help="don't show logo at startup")
        p.add_option("--pause", action="store_true", dest="pause", default=False,
                     help="don't close console window immediately")
        p.add_option("-d", "--debug", action="store_true", dest="debug", help="enable debug", default=False)
        p.add_option("--db", action="store", type="string", dest="db", help="database filename")
        p.add_option("-q", action="store_true",dest="quiet", help="print balance and exit", default=False)
        p.set_defaults(
            interactive=False,
            graph=None,
            imagefilename=None,
            nologo=False,
            debug=False
        )
        return p

    def interactive_mode_handler(self, opt, database_filename):
        try:
            a = True
            while a:
                a = raw_input("Login:")
                if a == '':
                    print("Incorrect data")
                    sys.exit(1)
                opt.login = a
                a = pass_from_db(opt.login, database_filename, opt)
                if a is None:
                    a = getpass.getpass("Password:")
                if a == '':
                    print("Incorrect data")
                    sys.exit(1)
                opt.password = a
                import_plot()
                if HAS_MATPLOT:
                    a = raw_input("Plot graph? [y/n]")
                    if a in ['y', 'Y']:
                        opt.graph = True
                        a = raw_input("Which kind of graph [time/traf]")
                        if a == 'time':
                            opt.graph = 'time'
                        elif a == 'traf':
                            opt.graph = 'traf'
                    elif a in ['n', 'N']:
                        opt.graph = False
                self.ui(opt)
                cont = False
                while True:
                    a = raw_input("Continue with another login [y/n]?")
                    if a == 'y':
                        cont = True
                        break
                    elif a == 'n':
                        cont = False
                        break
                if cont:
                    continue
                else:
                    break
        except Exception as e:
            print(e)
            sys.exit(1)

    def list_checker_handler(self, opt):
        try:
            list = open(opt.check_list, 'rt')
            for line in list:
                lp = line.strip().partition(':')
                if lp[2] == '':
                    continue
                print(lp[0].center(40, '*'))
                opt.login = lp[0]
                opt.password = lp[2]
                if opt.imagefilename:
                    fname = opt.imagefilename
                    # Заменим имя файла на логин
                    basename = os.path.basename(fname)
                    no_ext = basename.partition('.')[0]
                    fname = fname.replace(no_ext, lp[0])
                    show = False
                else:
                    fname = None
                    show = True
                opt.imagefilename = fname
                self.ui(opt)
                print("".center(40, '*') + '\n')
        except IOError as e:
            print("%s" % e)

    def non_interactive_mode_handler(self, opt, database_filename):
        if not opt.login:
            sys.exit()
        if not opt.password:
            opt.password = pass_from_db(opt.login, database_filename, opt)
            if not opt.password:
                print("Login not found")
                sys.exit(1)
        # command line
        self.ui(opt)

    def main(self):
        parser = self.setup_cmd_parser()
        # print help
        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit()

        opt, args = parser.parse_args()

        # Enable/Disable Debug mode
        byflyuser._DEBUG_ = opt.debug
        log_level = logging.DEBUG if opt.debug else logging.ERROR
        logging.basicConfig(stream=sys.stdout, level=log_level)

        # pause at exit?
        if opt.pause:
            atexit.register(pause)

        if not opt.nologo and not opt.quiet:
            parser.print_version()
        database_filename = opt.db if opt.db else _DEFAULT_DATABASE_FILENAME
        if opt.interactive:
            self.interactive_mode_handler(opt, database_filename)
        elif opt.check_list:
            self.list_checker_handler(opt)
        else:
            self.non_interactive_mode_handler(opt, database_filename)


if __name__ == "__main__":
    Program().main()
