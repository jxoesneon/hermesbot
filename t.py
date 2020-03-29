from time import sleep as Sleep
from datetime import datetime
Now = datetime.now()
from datetime import time as Time
from apscheduler.schedulers.background import BackgroundScheduler as Scheduler


# Start the scheduler
sched = Scheduler()
sched.start()


def ping():
    count = 0
    while True:
        count += 1
        print(f"ping {count}")
        Sleep(1)


exec_date = Time(7, 11, 0)


# Store the job in a variable in case we want to cancel it
job = sched.add_job(ping, "cron", hour=19, minute=45, second=0)

while True:
    print("base")
    Sleep(1)