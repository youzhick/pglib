# pglib
Development helper tool for configuring PostgreSQL **preload_libraries** values.

**pglib** is a tool for configuring PostgreSQL **(shared/session/local)_preload_libraries** values. It dispays installed extensions for existing PostgreSQL instance and allows to select them via simple ASCII-UI.
Note that this is mostly a developer tool. I don't think enterprise DBAs would find pglib useful, but personally I always use it during PostgreSQL extensions development. I wrote it for myself and I hope it could be useful for someone else.

(See the bottom line for the basic hotkey hints and notice that Home/End/PgUp/PgDown are supported too)
![Screenshot](/pglib_screen.png)

# Prerequisites and installation
**pglib** does not require installation, it only require python and **curses** (**ncurses**) library. It's also expected that you have a PostgreSQL instance installed and a local cluster inited. **pglib** will search for the installed extensions using **pg_config** tool and it needs the data directory path to search for config file(s).

# How it works
The current values for **shared_preload_libraries, session_preload_libraries and local_preload_libraries** are read **from postgresql.conf** and **postgresql.auto.conf** files. The resulting constants are written into **postgresql.auto.conf** file (preserving the other parameters of course). The list of the installed extensions is formed based on the **lib/share** directories contents, while the directories paths are acquired via **pg_config** tool. The last saved values is also stored in **~/.pglib.last** file allowing **pglib** to repeat the last selection even if the cluster configs are already rewritten.

# Configuring
## Usage:
pglib.py [\<option\>] [--pgdata=\<PGDATA\>] [--pginstall=\<PGINSTALL\>] [--pgconfig=\<PGCONFIG\>]
## Options:
- --help : Print help.
- --last : Repeat writing the last saved config. No UI.
- --info : Gather info about system, print it and exit. Use it as diagnostics in case of problems.
- --version : Print the program version.

**pglib** uses three parameter constants for finding PostgreSQL instance parts. Each of them can be set either as an environment variable or via command line parameter:
* **PGDATA**: Same as the traditional value: the directory containing cluster files. **postgresql.auto.conf** is supposed to be there already. And this is one of the places to search for **postgresql.conf**.
* **PGINSTALL**: The directory containing PostgreSQL binaries. The program will search for **pg_config** in **PGINSTALL/bin** (or in **$PATH** if **PGINSTALL** isn't set). This is the directory you set for **--prefix** while **configure**'ing PostgreSQL build.
* **PGCONFIG**: Additional directory to search for **postgresql.conf** in case it's not located in **PGDATA**. You can acquire the file location via *'SHOW config_file'* request to your DB.
None of the parameters are required, but these help to find the required data.\
What is really required:
1. **postgresql.auto.conf** file. We will rewrite it, but it should be there, otherwise something is wrong with the system setup. The file is expected to be in **PGDATA**. **PGDATA** is read either from the corresponding parameter/environment constant or from the **data_directory** value of **postgresql.conf** file if **PGCONFIG** is given.
2. **lib/share** directories. These are requested from **pg_config** which is expected to be found either in **PGINSTALL/bin** or somewhere in the system **$PATH**.

**Hint**: use --info option to see which paths will be used for your system.

## Just for example: how do I configure it
I always have **$PGDATA** environment variable set to my cluster data directory path and **$PGINSTALL** - to my PostgreSQL installation. I also use these environment variables for postgres build and **initdb**. My configs are always located in **$PGDATA** and this allows me to simply run **pglib** without parameters.

# Convenience notes
There are several unobvious features that speed-up the work with **pglib** a lot:
* --last option. It just reqrites the same **preload_libraries** values you have written the last time using UI, but now - instantly, skipping the selection stage. Very useful then you frequently rebuild/reinit everything.
* Quick search. When in UI mode, start typing something and the cursor will move to the corresponding extension name. The currently typed character sequence will be displayed near the bottom-right corner of the screen. Note that the typed string do not need to be at the beginning of the extension name. For example (see the screenshot above), when I need to find **pg_proaudit** extension, I just type *'aud'* and voila! The cursor moves to the extension name, in which the search string orrures first, starting the search from the position right after the current cursor position. This means that if you have two extension with *'foo'* in their names, the first typing of *'foo'* will bring the cursor to the first of them, while the retyping will bring it to the second one.
* Selection order. When you select an extension, it's name is added to the end of the corresponding preload-constant. It helps to change the extensions order if required. Just unselect and select again an extension to move it to the end of the list.
