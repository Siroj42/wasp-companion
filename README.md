## Wasp Companion

This is a Linux companion app for [wasp-os](https://github.com/daniel-thompson/wasp-os), a smartwatch operating system. It's written in Python with GTK and Libhandy.

This software is early in development so things are guaranteed to break.

### Functionality

On the front end, this app will:

- Show a graph of heartbeat data
- Show a graph of step counter data
- Add, update or remove apps
- Update wasp-os (DFU)
- Present settings (brightness, bluetooth, notifications, set a watchface, go to the bootloader, turn on the flashlight, restart the watch)

Behind the scenes, it will:

- Synchronize the time on the watch (RTC)
- Control music that's playing on your phone
- Sync the timer and stopwatch with the Clock app on your phone

### Building

Start by running `git submodule init` and `git submodule update` in the project's root directory.

I've made a simple helper script to automate the build process of this project. Enter the `flatpak` directory and run `./flatpak` to see build commands. Run `./flatpak -f` to install build dependencies, update python modules and build the flatpak. When building is finished, you can run `./flatpak -p` to run the app. Be aware that building the app like this will not make it show up in your app list, and I'm not sure why.

To rebuild modules (`./flatpak -m`), you need `pip3` installed locally.

### Credits

- [Daniel Thompson](https://github.com/daniel-thompson) for creating wasptool and its dependencies, which this app uses in the background.
- [Maarten de Jong](https://github.com/daniel-thompson) for writing the first 61 lines of code.

### Useful links

- [Python GTK reference](https://lazka.github.io/pgi-docs/)
