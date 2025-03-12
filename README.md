Process:
- driver function (test.py)
- load configuration data (config.Config)
- build a request (request.Request)
- download the data from finance server (downloader.Downloader)
- build a frame with the data (frame.Frame)
  - moving averages & differences
  - buffers
  - recommendations
- build the objective function (objective_function.ObjectiveFunction)
- build plots
  - of_plotter.ObjectiveFunctionPlotter
  - ts_plotter.TimeSeriesPlotter

NB:
- All dates are stored in classes in datetime format

usage:
/bin/csh
conda activate dev
python test.py


For MAD
Step 1: Calculate Moving Averages and MAD
We'll calculate the short-term and long-term moving averages, then compute the Moving Average Distance.

Step 2: Calculate Returns and Create Predictor
We'll compute the returns and create a binary predictor based on MAD.

Step 3: Visualization and Analysis
We'll visualize the relationship between MAD and equity returns.
