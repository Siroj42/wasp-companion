# Health API

Wasp Companion gives other applications to access wasp-os' step counter (and maybe other things in the future) through a DBus Interface. This data is represented as a list of activities. It makes it available at the bus name `io.github.siroj42.WaspCompanion`, but other applications could also expose the same interface on their own bus names. The paths and interfaces are named according to the API version, so API version 1 is exposed through the interface `io.github.siroj42.HealthAPI1` on the path `/io/github/siroj42/HealthAPI1`. All interfaces are documented in the DBus XML files in the `src/dbus/` directory, and an example implementation of the health app part of the API is available in `docs/healthapp-example.py`.

## Detection

To allow multiple companion apps and multiple health apps to make use of this API, there has to be a way for them to detect each other. For this purpose, the bus name `io.github.siroj42.HealthApp` is reserved. Because we can assume that companion apps are running in the background, they can listen for the `org.freedesktop.DBus.NameOwnerChanged` signal (see <https://dbus.freedesktop.org/doc/dbus-specification.html#bus-messages-name-owner-changed>). When the user of a health app wants to connect it to their companion app, the health app claims this bus name and exposes the interface `io.github.siroj42.HealthApp1` on the path `/io/github/siroj42/HealthApp1`. In response, any companion app that is currently running announces itself using the `Announce` method on that interface. The user can then choose the right companion app in the respective menu of their health app. 