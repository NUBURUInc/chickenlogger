# import nidaqmx

# with nidaqmx.Task() as task:
#     task.ai_channels.add_ai_voltage_chan("Dev4/ai0")
#     print(task.read())

# """Example for reading singals for every n samples."""

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')
import pprint
# import time

import nidaqmx
from nidaqmx.constants import AcquisitionType

import collections

# Define buffer
bufsize = 10000
databuffer1 = collections.deque([0.0] * bufsize, bufsize)
databuffer2 = collections.deque([0.0] * bufsize, bufsize)
databuffer3 = collections.deque([0.0] * bufsize, bufsize)
databuffer4 = collections.deque([0.0] * bufsize, bufsize)

pp = pprint.PrettyPrinter(indent=4)

def testmeth():

    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan("Dev4/ai0")
        task.ai_channels.add_ai_voltage_chan("Dev4/ai1")
        task.ai_channels.add_ai_voltage_chan("Dev4/ai2")
        task.ai_channels.add_ai_voltage_chan("Dev4/ai3")
        task.timing.cfg_samp_clk_timing(1000, sample_mode=AcquisitionType.CONTINUOUS)
        # samples = []

        def callback(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
            """Callback function for reading singals."""
            print("Every N Samples callback invoked.")
            # samples.extend(task.read(number_of_samples_per_channel=1000))

            retval = task.read(number_of_samples_per_channel=1000)

            # print(retval[0])

            databuffer1.extend(retval[0])
            databuffer2.extend(retval[1])
            databuffer3.extend(retval[2])
            databuffer4.extend(retval[3])
            return 0

        task.register_every_n_samples_acquired_into_buffer_event(1000, callback)
        task.start()
        input("Running task. Press Enter to stop and see number of accumulated samples.\n")
        # time.sleep(10)
        print(len(databuffer1))

testmeth()

# plt.figure(1)
plt.plot(databuffer1, label='1')
plt.plot(databuffer2, label='2')
plt.plot(databuffer3, label='3')
plt.plot(databuffer4, label='4')
plt.figure()
plt.show()