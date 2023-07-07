# PPM Pro Command Line client
This project is a small CLI interface to PPM Pro.  It has the ability
to set daily hours on each activity and run a report of hours for a
given timesheet.

It has the ability to automatically look up daily hours from an
external source via the `get_hours()` hook, although this
funcionality is left unimplemented by default as there is no
standard way of doing this.

It is suitable for running out of cron to automatically set hours each day.

## Requirements/Usage
The tool is written in Python and requires the availability of a
supported Python3 interpreter.  All the modules required should be
part of a typical base install.

You will need to modify the value of the `org_name` constant
near the top of the file.  This should be the same as the first
part of your PPM Pro URL (e.g. https://foo.ppmpro.com would use
org_name foo).

## Authentication
Per https://success.planview.com/Planview_PPM_Pro/150_PPM_Pro_Administrator_Documentation/015_System_Settings/010_Authentication
and https://success.planview.com/Planview_PPM_Pro/Reports_and_Dashboards/020_Reports/040_OData_Setup#section_2
if your instance of PPM Pro uses SAML (which apparently is their
recommendation and I suspect what most sites implement), you do not
currently appear to be able to use an API key for authentication even
if you follow Planview's instructions for generating one in the app.
This appears to be an internal limitation on the site URL, as the
token does work as described for the OData endpoints.

As a result, for now the only way to authenticate appears to be to
present a valid session cookie.  The tool expects this cookie to be
stored locally on the filesystem, by default in `~/.ppmpro.session`,
although that location can be overridden with a command line flag.

The user will need to log in to the webapp the first time and obtain
a suitable cookie from their browser storage.  A valid session cookie
will be of the form:
```
RKVM_SID=some-uuid-string
```

## Known Issues
* Due to the way authentication is handled (see above), you will need
to make sure the tool is called regularly to keep your stored session
active.  Once an hour seems to work.  Calling the tool without any
arguments issues a simple API GET request that is sufficient for this.

* The `get_hours()` method implementation is left as an exercise
to the reader.  The example implementation simply divides a target
daily number of hours evenly among all activities.  This probably does
not reflect reality.
