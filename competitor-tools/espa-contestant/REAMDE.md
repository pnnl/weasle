This directory holds sample competitor algorithms written in Python.

dummy_algorithm.py:

	Computes an offer based on forecasted prices (LMP). This algorithm first computes an optimal (profit maximizing) charge/discharge schedule based on prices. It then computes the opportunity cost of charging/discharging in other windows and submits these as its offer. For the RTM a SoC bidding scheme is used with offers derived from the DAM prices.

constant_offer.py:
(requres offer_utils.py)

	Computes a constant offer with no regard to prices (LMP). Allows the offer to be modified within offer_utils.py. Default offer is to submit a bid of $0. Block offers may be included. 
