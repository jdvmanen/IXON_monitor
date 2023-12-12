Tool to monitor IXON adapter connection state. It shows a banner on top of your screen with the IXON adapter status.
It shows the client device name in the banner as well.
 
#### How to install ####
* Make sure your IXON network adapter is called 'IXON'.
* winget install python
* pip install tkinter
* pip install psutil
* place script (with extension .pyw) in shell:startup


#### How to use ####
Shows a little 'Not actief' (White) indicator on top of your screen if no IXON connection is active.
shows up as soon as the IXON adapter is active with a banner red/white alterating.
If you click on it, it moves 500 pixels to the right or to the left (to prevent something
being behind the indicator that has to be read)
