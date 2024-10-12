## multi-receipt-splitter

Did different friends pay for receipts that all need to be split? This script will aggregate everything and output who should pay who in order to settle all differences!

Usage:
* Create a new input text file for the collection of receipts you want to split
* See `custom_format_spec.txt` and `sample_file.txt` for how to write your own input text file
* After creating a text file, run the script with `python receipt_splitter.py [input file path]`

Features:
* Custom input format designed to minimize typing required
* Aggregates transactions together to minimize # of payments necessary to settle all balances

Warning:
* This script is meant for personal use among friends, so rounding errors are not accounted for. Typically, differences of a cent or two can be expected for a handful of receipts and items.
