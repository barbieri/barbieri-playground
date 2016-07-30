Tools to help use "taskjuggler" without its GUI and produce nice reports.

This package provides tools that will provide nice reports
(taskjuggler-report), gantt charts (taskjuggler-gantt) and time shift
the whole taskjuggler project file (taskjuggler-timeshift).

The best thing is that you don't need to use Graphical User Interfaces
for that, so these can be automated from cron jobs, web servers and
makefiles.

Reports are generated using LaTeX syntax since I use them in my LaTeX
files easily, but we can easily add code to generate HTML reports as
well in future.

Requires:
 * PyX: used by taskjuggler-gantt to draw charts.
 * Python >= 2.5, not tested with 2.6 or 3.0 yet.
