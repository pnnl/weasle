# espa-market-shell
Simplified wholesale market simulator for ESPA contestants

This market shell does not perform any market clearing, dispatch,
or settlement. Instead, it sends the necessary input files (with
dummy values) to the correct directories, then validates that the
offer file submitted by your algorithm is in the correct format.

To test:

1. make a directory in offer_data called 'participant_p00001'.
2. Place your algorithm in 'offer_data/participant_p00001'.
3. Run market_simulator.py -a [name_of_your_algorithm.py]

The market simulator accepts input other input arguments to
change the market type and duration of the test.

Once you have the input/output formatting correct, you may make a
Sandbox submission through the ESPA-Comp website to get feedback
on the performance of your code in a full market clearing
simulation.
