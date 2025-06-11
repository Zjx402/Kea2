# Launch Kea2 and load one single script quicktest.py.
cmd='kea2 run -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 5 --max-step 30 --take-screenshots --throttle 200 --driver-name d unittest discover -s "$(pwd)/.." -p quicktest.py'
echo $cmd
eval $cmd