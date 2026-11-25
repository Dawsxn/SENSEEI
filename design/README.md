# Design sources

Screen and logo designs as static mockups. Not a prototype, and not the app.

Each `.dc.html` file is one artboard. `canvas.json` lays them out. Together they
assemble into a single pan-and-zoom canvas, which is what you actually look at.

**The assembled canvas is not committed.** It embeds a whole editor and runs to
about 2 MB per build, so `.gitignore` keeps `design/**/*.html` out while allowing
`design/**/*.dc.html` through. Edit the sources, then rebuild.

Rebuilding is done by the `/design` skill in Claude Code, which owns the assembly
step. Ask it to rebuild the canvas from the sources in this directory.

To regenerate a single PNG without building the whole canvas:

```
python scripts/render_artboard.py design/ReadingStep.dc.html design/png/03c-reading-step.png 1440 900 "state=Reading"
```

## The screens

Click any of these to view it. `png/` is regenerated from the sources whenever a
design changes, so it always matches.

| Screen | Image |
| --- | --- |
| Sign in | [png/01-sign-in.png](png/01-sign-in.png) |
| Reading list (replaced by the three below) | [png/02-reading-list.png](png/02-reading-list.png) |
| Student classes | [png/02c-student-classes.png](png/02c-student-classes.png) |
| Student class | [png/02d-student-class.png](png/02d-student-class.png) |
| Student reading | [png/03d-student-reading.png](png/03d-student-reading.png) |
| Join a class | [png/02b-join-class.png](png/02b-join-class.png) |
| Join a class, wrong code | [png/02b-join-wrong.png](png/02b-join-wrong.png) |
| Reading detail, full page | [png/03-reading-detail.png](png/03-reading-detail.png) |
| Reading detail, dialog | [png/03b-reading-detail-dialog.png](png/03b-reading-detail-dialog.png) |
| Walkthrough, 1 of 3 | [png/03e-walkthrough-1.png](png/03e-walkthrough-1.png) |
| Walkthrough, 2 of 3 | [png/03e-walkthrough-2.png](png/03e-walkthrough-2.png) |
| Walkthrough, 3 of 3 | [png/03e-walkthrough-3.png](png/03e-walkthrough-3.png) |
| Help icon on the reading page | [png/03e-help-icon.png](png/03e-help-icon.png) |
| Before you start, with the concept | [png/03e-before-you-start.png](png/03e-before-you-start.png) |
| Reading step, intro dialog | [png/03c-reading-step-intro.png](png/03c-reading-step-intro.png) |
| Reading step | [png/03c-reading-step.png](png/03c-reading-step.png) |
| Reading step, text fallback | [png/03c-reading-step-text.png](png/03c-reading-step-text.png) |
| Reading step, leaving before Done | [png/03c-reading-step-leave.png](png/03c-reading-step-leave.png) |
| Tutoring session | [png/04-tutoring-session.png](png/04-tutoring-session.png) |
| Tutoring session, PDF reading | [png/04b-tutoring-pdf-reading.png](png/04b-tutoring-pdf-reading.png) |
| Criterion feedback, six approaches | [png/04c-criterion-feedback.png](png/04c-criterion-feedback.png) |
| Reference panel, components | [png/04d-panel-components.png](png/04d-panel-components.png) |
| Reference panel, rubric | [png/04d-panel-rubric.png](png/04d-panel-rubric.png) |
| Session review, student | [png/05-session-review.png](png/05-session-review.png) |
| Session review, instructor | [png/05b-session-review-instructor.png](png/05b-session-review-instructor.png) |
| Session review, student (replaces the two above) | [png/05c-session-review-student.png](png/05c-session-review-student.png) |
| Session review, instructor (replaces the two above) | [png/05c-session-review-instructor.png](png/05c-session-review-instructor.png) |
| Session review, rubric opened from a tag | [png/05c-session-review-rubric.png](png/05c-session-review-rubric.png) |
| Session end, passed | [png/05d-1-passed.png](png/05d-1-passed.png) |
| Session end, passed, phone | [png/05d-1-passed-phone.png](png/05d-1-passed-phone.png) |
| Session end, out of tries | [png/05d-2-failed.png](png/05d-2-failed.png) |
| Session end, out of tries, phone | [png/05d-2-failed-phone.png](png/05d-2-failed-phone.png) |
| Session error, no connection | [png/05d-3-offline.png](png/05d-3-offline.png) |
| Session error, no connection, phone | [png/05d-3-offline-phone.png](png/05d-3-offline-phone.png) |
| Session error, answer failed | [png/05d-4-sendfail.png](png/05d-4-sendfail.png) |
| Session error, answer failed, phone | [png/05d-4-sendfail-phone.png](png/05d-4-sendfail-phone.png) |
| Session error, start failed | [png/05d-5-startfail.png](png/05d-5-startfail.png) |
| Session error, start failed, phone | [png/05d-5-startfail-phone.png](png/05d-5-startfail-phone.png) |
| Reading failed, tutoring screen | [png/05d-6-tutorfail.png](png/05d-6-tutorfail.png) |
| Reading failed, tutoring screen, phone | [png/05d-6-tutorfail-phone.png](png/05d-6-tutorfail-phone.png) |
| Reading failed, reading step | [png/05d-7-readfail.png](png/05d-7-readfail.png) |
| Reading failed, reading step, phone | [png/05d-7-readfail-phone.png](png/05d-7-readfail-phone.png) |
| Reading not available | [png/05d-8-readmissing.png](png/05d-8-readmissing.png) |
| Reading not available, phone | [png/05d-8-readmissing-phone.png](png/05d-8-readmissing-phone.png) |
| Page not found | [png/08-notfound.png](png/08-notfound.png) |
| Page not found, phone | [png/08-notfound-phone.png](png/08-notfound-phone.png) |
| Page crashed | [png/08-crash.png](png/08-crash.png) |
| Page crashed, phone | [png/08-crash-phone.png](png/08-crash-phone.png) |
| Instructor classes, cards (replaces the two below) | [png/06c-1-list.png](png/06c-1-list.png) |
| Instructor classes, cards, phone | [png/06c-1-list-phone.png](png/06c-1-list-phone.png) |
| Instructor classes, none | [png/06c-2-empty.png](png/06c-2-empty.png) |
| Instructor classes, loading | [png/06c-3-loading.png](png/06c-3-loading.png) |
| New class (replaces the one below) | [png/06c-5-new-typed.png](png/06c-5-new-typed.png) |
| New class, phone | [png/06c-5-new-typed-phone.png](png/06c-5-new-typed-phone.png) |
| Class, Readings tab (replaces Class below) | [png/06d-01-readings.png](png/06d-01-readings.png) |
| Class, Readings tab, phone | [png/06d-01-readings-phone.png](png/06d-01-readings-phone.png) |
| Class, Add reading | [png/06d-02-add-menu.png](png/06d-02-add-menu.png) |
| Class, Choose from your readings | [png/06d-03-picker.png](png/06d-03-picker.png) |
| Class, class menu | [png/06d-04-more-menu.png](png/06d-04-more-menu.png) |
| Class, Students tab | [png/06d-05-students.png](png/06d-05-students.png) |
| Class, Students tab, phone | [png/06d-05-students-phone.png](png/06d-05-students-phone.png) |
| Class, student menu | [png/06d-06-student-menu.png](png/06d-06-student-menu.png) |
| Class, Statistics tab | [png/06d-07-stats.png](png/06d-07-stats.png) |
| Class, Statistics tab, phone | [png/06d-07-stats-phone.png](png/06d-07-stats-phone.png) |
| Class, no readings | [png/06d-08-readings-empty.png](png/06d-08-readings-empty.png) |
| Class, no students | [png/06d-09-students-empty.png](png/06d-09-students-empty.png) |
| Class, no statistics | [png/06d-10-stats-empty.png](png/06d-10-stats-empty.png) |
| Class, a student in it | [png/06d-11-student-page.png](png/06d-11-student-page.png) |
| Class, a student in it, phone | [png/06d-11-student-page-phone.png](png/06d-11-student-page-phone.png) |
| Reading in a class, with the Flagged box | [png/06e-1-students.png](png/06e-1-students.png) |
| Reading in a class, phone | [png/06e-1-students-phone.png](png/06e-1-students-phone.png) |
| Reading in a class, Statistics | [png/06e-2-stats.png](png/06e-2-stats.png) |
| Reading in a class, Statistics, phone | [png/06e-2-stats-phone.png](png/06e-2-stats-phone.png) |
| A student's sessions on a reading | [png/06e-3-student.png](png/06e-3-student.png) |
| A student's sessions on a reading, phone | [png/06e-3-student-phone.png](png/06e-3-student-phone.png) |
| Instructor review, breadcrumb to the student | [png/06e-4-review.png](png/06e-4-review.png) |
| Instructor review, phone | [png/06e-4-review-phone.png](png/06e-4-review-phone.png) |
| Instructor classes | [png/06-classes.png](png/06-classes.png) |
| Instructor classes, empty | [png/06-classes-empty.png](png/06-classes-empty.png) |
| New class | [png/06-new-class.png](png/06-new-class.png) |
| Class | [png/06b-class.png](png/06b-class.png) |
| Edit class | [png/06b-class-edit.png](png/06b-class-edit.png) |
| Delete class | [png/06b-class-delete.png](png/06b-class-delete.png) |
| Instructor readings | [png/07-readings.png](png/07-readings.png) |
| Instructor readings, empty | [png/07-readings-empty.png](png/07-readings-empty.png) |
| Upload, choose a PDF | [png/07b-upload-pdf-empty.png](png/07b-upload-pdf-empty.png) |
| Upload, PDF chosen | [png/07b-upload-pdf.png](png/07b-upload-pdf.png) |
| Upload, no text found | [png/07b-upload-no-text.png](png/07b-upload-no-text.png) |
| Upload, reading the PDF | [png/07b-upload-loading.png](png/07b-upload-loading.png) |
| Upload, check the text | [png/07b-upload-text.png](png/07b-upload-text.png) |
| Upload, figures not described | [png/07b-upload-figures-failed.png](png/07b-upload-figures-failed.png) |
| Upload, details | [png/07b-upload-details.png](png/07b-upload-details.png) |
| Upload, no classes ticked | [png/07b-upload-no-classes.png](png/07b-upload-no-classes.png) |
| Upload, leave | [png/07b-upload-leave.png](png/07b-upload-leave.png) |
| Reading, instructor | [png/07c-reading.png](png/07c-reading.png) |
| Reading, instructor, text | [png/07c-reading-text.png](png/07c-reading-text.png) |
| Edit reading | [png/07c-reading-edit.png](png/07c-reading-edit.png) |
| Reading classes | [png/07c-reading-classes.png](png/07c-reading-classes.png) |
| Reading classes, none ticked | [png/07c-reading-no-classes.png](png/07c-reading-no-classes.png) |
| Delete reading | [png/07c-reading-delete.png](png/07c-reading-delete.png) |
| Readings, phone | [png/07d-mobile-readings.png](png/07d-mobile-readings.png) |
| Upload text step, phone | [png/07d-mobile-upload-text.png](png/07d-mobile-upload-text.png) |
| Reading, instructor, phone | [png/07d-mobile-reading.png](png/07d-mobile-reading.png) |
| Class, with statistics | [png/08-class-stats.png](png/08-class-stats.png) |
| Class, no sessions yet | [png/08-class-no-sessions.png](png/08-class-no-sessions.png) |
| Reading in a class | [png/08b-class-reading.png](png/08b-class-reading.png) |
| Reading in a class, no sessions | [png/08b-class-reading-no-sessions.png](png/08b-class-reading-no-sessions.png) |
| Reading in a class, no students | [png/08b-class-reading-no-students.png](png/08b-class-reading-no-students.png) |
| Class, phone | [png/08c-mobile-class.png](png/08c-mobile-class.png) |
| Trial: sign in with an ID | [png/09-trial-sign-in.png](png/09-trial-sign-in.png) |
| Trial: sign in, wrong ID | [png/09-trial-sign-in-wrong.png](png/09-trial-sign-in-wrong.png) |
| Trial: sign in, ID no longer active | [png/09-trial-sign-in-closed.png](png/09-trial-sign-in-closed.png) |
| Trial: reading, with the countdown | [png/09b-trial-reading.png](png/09b-trial-reading.png) |
| Trial: tutoring, with the countdown | [png/09b-trial-tutoring.png](png/09b-trial-tutoring.png) |
| Trial: pre-test, start | [png/10-trial-pretest-start.png](png/10-trial-pretest-start.png) |
| Trial: pre-test | [png/10-trial-pretest.png](png/10-trial-pretest.png) |
| Trial: pre-test, submit | [png/10-trial-pretest-submit.png](png/10-trial-pretest-submit.png) |
| Trial: pre-test, time up | [png/10-trial-pretest-time-up.png](png/10-trial-pretest-time-up.png) |
| Trial: post-test, start | [png/10b-trial-posttest-start.png](png/10b-trial-posttest-start.png) |
| Trial: post-test, Part A | [png/10b-trial-posttest.png](png/10b-trial-posttest.png) |
| Trial: post-test, Part C | [png/10b-trial-posttest-written.png](png/10b-trial-posttest-written.png) |
| Trial: post-test, Part D | [png/10b-trial-posttest-grouping.png](png/10b-trial-posttest-grouping.png) |
| Trial: post-test, submit | [png/10b-trial-posttest-submit.png](png/10b-trial-posttest-submit.png) |
| Trial: SEE-I answer box, typing | [png/10f-trial-session-typing.png](png/10f-trial-session-typing.png) |
| Trial: SEE-I session complete | [png/10f-trial-session-complete.png](png/10f-trial-session-complete.png) |
| Trial: SEE-I out of attempts | [png/10f-trial-session-out-of-attempts.png](png/10f-trial-session-out-of-attempts.png) |
| Trial: SEE-I time up | [png/10f-trial-session-time-up.png](png/10f-trial-session-time-up.png) |
| Trial: done | [png/10c-trial-done.png](png/10c-trial-done.png) |
| Trial: done, time up | [png/10c-trial-done-time-up.png](png/10c-trial-done-time-up.png) |
| Trial: grading | [png/11-trial-grading.png](png/11-trial-grading.png) |
| Trial: grading, no answer | [png/11-trial-grading-no-answer.png](png/11-trial-grading-no-answer.png) |
| Trial: grading, all graded | [png/11-trial-grading-graded.png](png/11-trial-grading-graded.png) |
| Trial: the grader's view | [png/11-trial-grader.png](png/11-trial-grader.png) |
| Trial: new class, tests off | [png/11b-trial-new-class-tests.png](png/11b-trial-new-class-tests.png) |
| Trial: edit class, with tests | [png/11b-trial-edit-class-tests.png](png/11b-trial-edit-class-tests.png) |
| Trial: the last five minutes | [png/09b-trial-last-minutes.png](png/09b-trial-last-minutes.png) |
| Trial: done early | [png/09c-trial-done.png](png/09c-trial-done.png) |
| Trial: time's up | [png/09c-trial-time-up.png](png/09c-trial-time-up.png) |
| Trial: classes with a mode | [png/10-trial-classes.png](png/10-trial-classes.png) |
| Trial: new class | [png/10-trial-new-class.png](png/10-trial-new-class.png) |
| Trial: a class | [png/10a-trial-class.png](png/10a-trial-class.png) |
| Trial: a reading in a class | [png/10a-trial-class-reading.png](png/10a-trial-class-reading.png) |
| Trial: participant batches | [png/10b-participants.png](png/10b-participants.png) |
| Trial: no batches yet | [png/10b-participants-empty.png](png/10b-participants-empty.png) |
| Trial: new batch | [png/10b-new-batch.png](png/10b-new-batch.png) |
| Trial: a batch | [png/10c-batch.png](png/10c-batch.png) |
| Trial: close a batch | [png/10c-batch-close.png](png/10c-batch-close.png) |
| Trial: void an ID | [png/10c-batch-void.png](png/10c-batch-void.png) |
| Trial: printed slips | [png/10d-slips.png](png/10d-slips.png) |
| Trial: download data | [png/10e-download.png](png/10e-download.png) |
| Trial: withdraw a participant | [png/10e-withdraw.png](png/10e-withdraw.png) |
| Trial chatbot: before you start | [png/11-chatbot-intro.png](png/11-chatbot-intro.png) |
| Trial chatbot: empty | [png/11-chatbot.png](png/11-chatbot.png) |
| Trial chatbot: chatting | [png/11-chatbot-chatting.png](png/11-chatbot-chatting.png) |
| Trial chatbot: finish | [png/11-chatbot-finish.png](png/11-chatbot-finish.png) |
| Trial chatbot: done | [png/11-chatbot-done.png](png/11-chatbot-done.png) |
| Trial chatbot: time's up | [png/11-chatbot-time-up.png](png/11-chatbot-time-up.png) |
| Trial reading only: before you start | [png/11b-reading-only-intro.png](png/11b-reading-only-intro.png) |
| Trial reading only | [png/11b-reading-only.png](png/11b-reading-only.png) |
| Trial reading only: finish | [png/11b-reading-only-finish.png](png/11b-reading-only-finish.png) |
| Trial reading only: done | [png/11b-reading-only-done.png](png/11b-reading-only-done.png) |
| Reading in a class, phone | [png/08c-mobile-class-reading.png](png/08c-mobile-class-reading.png) |

Do not open a `.dc.html` in a browser expecting to see the screen. It renders a
grey skeleton with `{{placeholder}}` text, because repeated rows and every
colour come from template values the canvas runtime supplies, and `support.js`
is not in this repository. The PNGs are what the screens look like.

## What is here

`design/` holds the app screens, `design/logo/` holds logo explorations.

Several artboards carry a Scenario or State control above them, which switches
between cases rather than duplicating the artboard. Artboard 3 and 3b cover four
history states each; 3c covers its opening dialog, a reading with a stored PDF,
and one without;
artboard 5 shows a complete session and 5b a failed one.

## Decisions these record

- **3b is the chosen direction** for reading detail. 3 is kept for comparison.
- **4b is shipped, not a comparison.** It was drawn as one, arguing that storing
  only the extracted text was enough. That argument rested on the agents being
  the only readers, which stopped being true once the student reads the document
  itself. `docs/context/data-model.md` records the reversal.
- **4c chose A**, tags under the message. The Tutor Agent stops naming the
  criteria in its prose as of prompt v2, so the interface labels them instead.
  The other five are kept because the comparison is the argument: C and D cost
  nothing on the backend, and losing that would make A look free.
- **4d is where the vocabulary is explained.** Tags carry only names, which is
  affordable because the rubric panel carries what each one asks for, in the
  rubric's own words.
- **3c is the step the app used to skip.** `student-tutoring-loop.md` has always
  called for the student to read first and say so explicitly; the earlier
  mockups folded that into the split screen.
- **The logo is unresolved.** The mark used across the screens is direction A
  from `design/logo/`, standing in as a placeholder. The wordmark sets SEE-I in
  the accent colour, since the framework name sits inside the product name.

## Relationship to the design system

`docs/context/design-system.md` is authoritative for tokens and component
conventions. These files should follow it, not the other way round.

The mockups are hand-written HTML that imitates shadcn, because artboards cannot
run React. Where a mockup and a real shadcn component disagree, the component
wins. The mockups specify layout, copy, states and behaviour, not component
internals.
