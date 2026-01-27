'''
Views & modals available in /my_lectures:

base command (read)
- view #1: pages of lecture data, with nav buttons and buttons linking to C,U,D functionalities (done)

new lecture flow (create):
- modal #1: fill in first set of fields -> submit
- view #2: display filled-in data, button to edit that data, fill in remaining stuff, cancel
- if edit go back to modal #1
- if continue modal #2 -> submit
- view #3: success / failure

modify lecture flow (update):
- view #4: display details, button to edit basic info, button to edit details, button to cancel, button to save
- if edit basic info: modal #1
- if edit details: modal #2
- if cancel: back to view #1
- if save: view #3 (operation can fail if lecture conflict for example)

cancel lecture flow (delete):
- view #5: "Are you sure you want to cancel", button "Keep lecture", button "Cancel lecture"
- if keep: back to view #1
- if cancel: 
'''



