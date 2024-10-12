import argparse
import copy
import math


class ReceiptData:
    def __init__(self, receipt_name, payer, price, price_after_tax_tip, people_item_list):
        self.receipt_name = receipt_name
        self.payer = payer
        self.price = price
        self.price_after_tax_tip = price_after_tax_tip
        self.people_item_list = people_item_list
        self.people_item_list_scaled = scale_items(people_item_list, price, price_after_tax_tip)


# Scale item prices by the tax/tip multiplier
def scale_items(people_item_list, price_before, price_after_tax_tip):
    scaled_item_list = []
    multiplier = price_after_tax_tip / price_before

    for d in people_item_list:
        scaled_item_list.append(copy.deepcopy(d))
        scaled_item_list[-1]["prices"] = [price * multiplier for price in scaled_item_list[-1]["prices"]]
    
    return scaled_item_list


# Given a list of parsed receipt data, calculate how much people should pay/receive
def calculate_money_deltas(receipt_list: list[ReceiptData], names: list[str]):
    # Positive amounts = money to be paid
    # Negative amounts = someone has paid more than what they should've
    money_deltas = [0] * len(names)

    for receipt in receipt_list:
        payer_idx = names.index(receipt.payer)
        money_deltas[payer_idx] -= receipt.price_after_tax_tip

        for i, d in enumerate(receipt.people_item_list_scaled):
            money_owed = sum(d["prices"])
            money_deltas[i] += money_owed
    
    assert math.isclose(sum(money_deltas), 0, abs_tol=1e-06)
    return money_deltas


def print_deltas(money_deltas, names):
    print()
    print("--- Final Balances ---")
    for amount, name in zip(money_deltas, names):
        if amount < 0:
            print(f"{name} should receive {round(-amount, 3)}")
        else:
            print(f"{name} should pay {round(amount, 3)}")


# Given a list of money deltas, find a list tuples (a, b, c) representing "a should pay b amount $c"
# that will settle all balances that people owe/should receive in ideally fewest transactions possible
def calculate_pay_transactions(money_deltas: list[float], names: list[str]):
    # Create a list of (name, delta) tuples and sort it from paid the most -> owes the most
    balances = sorted(zip(names, money_deltas), key=lambda x: -x[1])
    transactions = []
    i, j = 0, len(balances) - 1

    while i < j:
        person_paying, debt = balances[i]
        person_receiving, credit = balances[j]

        should_receive = -credit
        if debt > should_receive:
            # If person_paying owes more than what person_receiving should get,
            # then send as much as person_receiving should get
            transactions.append((person_paying, person_receiving, should_receive))
            balances[i] = (person_paying, debt - should_receive)
            balances[j] = (person_receiving, 0)
            j -= 1
        else:
            # Otherwise, person_paying should pay everything they can to the person_receiving
            transactions.append((person_paying, person_receiving, debt))
            balances[i] = (person_paying, 0)
            balances[j] = (person_receiving, credit + debt)
            i += 1

    return transactions


def print_transactions(transactions):
    print()
    print("--- Final Transactions ---")
    for person_paying, person_receiving, amount in transactions:
        print(f"{person_paying} -> {person_receiving}: {round(amount, 2)}")


# Parses a receipt section of the input file
# WARNING: program uses floats because friends don't care about cent differences :)
def parse_receipt(lines: list[str], names: list[str]) -> ReceiptData:
    num_people = len(names)
    receipt_name = clean_line("RECEIPT NAME:", lines[0])
    receipt_payer = clean_line("PAYER:", lines[1])
    total_price, total_price_after_tax_tip = parse_receipt_prices(lines[2])

    if receipt_payer not in names:
        raise Exception(f"Name '{receipt_payer}' not found in list of NAMES")

    # Parse all item lines
    cool_people_stuff = [{"item_names": [], "prices": []} for _ in range(len(names))]
    for line in lines[3:]:
        split_arr = [s.strip() for s in line.split(";")]
        
        if len(split_arr) == 1:
            # Handles first two cases
            #   Format 1: Split unnamed item among everyone
            #   Format 2: Split ITEM_NAME among everyone    
            item_price_str = split_arr[0]
            if "," not in split_arr[0]:
                # Converts format 1 into format 2
                item_price_str = "Unspecified Item, " + item_price_str

            item_name, price = parse_item_price_str(item_price_str)
            
            for person_data in cool_people_stuff:
                person_data['item_names'].append(item_name)
                person_data['prices'].append(price / num_people)
        elif len(split_arr) == 2:
            # Handles Format 3: Split ITEM_NAME among people listed evenly
            item_price_str, people_list_str = split_arr
            item_name, price = parse_item_price_str(item_price_str)
            people_list = [s.strip() for s in people_list_str.split(",")]

            # Split among specified people
            people_list = [int(x) for x in people_list]
            num_people = len(people_list)
            
            for person_idx in people_list:
                # Note: convert 1-index to 0-index
                cool_people_stuff[person_idx-1]['item_names'].append(item_name)
                cool_people_stuff[person_idx-1]['prices'].append(price / num_people)
        elif len(split_arr) == 3:
            # Handles Format 4: Split ITEM_NAME among people listed evenly by ratio 
            # (i.e. person_index_1 pays a ratio of ratio_1)
            item_price_str, people_list_str, ratios = split_arr
            item_name, price = parse_item_price_str(item_price_str)
            people_list = [int(x) for x in people_list_str.split(",")]
            ratios_list = [float(x) for x in ratios.split(",")]

            if len(people_list) != len(ratios_list):
                raise Exception(f"Mismatched lengths of people and ratio list: '{line}'")

            # Split among specified people with specific ratios
            num_people = len(people_list)
            ratio_sum = sum(ratios_list)
            for person, ratio in zip(people_list, ratios_list):
                cool_people_stuff[person-1]['item_names'].append(item_name)
                cool_people_stuff[person-1]['prices'].append(price * (ratio / ratio_sum))  # Scale price
        else:
            raise Exception(f"Misformatted ITEM line: '{line}'")

    return ReceiptData(receipt_name, receipt_payer, total_price, total_price_after_tax_tip, cool_people_stuff)


# Output receipt data nicely
def print_receipt(receipt: ReceiptData, names):
    output_header = f"--- RECEIPT: {receipt.receipt_name} ---"
    print(output_header)
    print(f"Payer:\t\t {receipt.payer}")
    print(f"Subtotal:\t {receipt.price}")
    print(f"Total:\t\t {receipt.price_after_tax_tip}")
    print(f"Tax + Tip rate:\t {receipt.price_after_tax_tip / receipt.price}")
    print()

    check_total = 0
    longest_name = max(len(name) for name in names) + 1  # Add one for the colon
    for name, stuff in zip(names, receipt.people_item_list_scaled):
        money_owed = sum(stuff['prices'])
        check_total += money_owed
        money_owed = round(money_owed, 2)

        # Print each person's owed, the stuff they got, and the price of each
        print(f"{(name + ':').ljust(longest_name)} {money_owed} \t {stuff['item_names']}")
        print(f"{''.ljust(longest_name)} {' ' * 5} \t {[round(x, 2) for x in stuff['prices']]}")

    # Make sure everything adds up
    print(f"Check total: {check_total}")
    assert math.isclose(check_total, receipt.price_after_tax_tip)
    
    print()
    print("Note: price list includes tax + tip multiplier")
    print("-" * len(output_header))


# Processes an input line by asserting that it starts with `prefix`
# Returns the same input line after removing `prefix` from it
def clean_line(prefix, line):
    if not line.startswith(prefix):
        raise Exception("Line does not start with expected prefix\n "
                        "Line: '" + line + "' \n Expected prefix: '" + prefix + "'")
    return line[len(prefix):].strip()


def parse_names(line):
    line = clean_line("NAMES:", line)
    return [name.strip() for name in line.split(",")]


def parse_receipt_prices(line):
    line = clean_line("PRICE:", line)
    prices = line.split(",")
    if len(prices) != 2:
        raise Exception(f"Receipt price line {line} does not contain two prices")
    
    return float(prices[0]), float(prices[1])


# Given a string containing "item, price", return item string and float price
def parse_item_price_str(item_price_str):
    item_price_list = [s.strip() for s in item_price_str.split(",")]
    if len(item_price_list) != 2:
        raise Exception(f"More than an item and price provided in string: {item_price_str}")

    return item_price_list[0].strip(), float(item_price_list[1])


# Partitions a list based on some separator
# In this program, we split the input into different receipts by "--"
def split_list_by_value(arr, value):
    result = []
    temp = []

    for item in arr:
        if item == value:
            if temp:
                result.append(temp)
                temp = []
        else:
            temp.append(item)

    if temp:
        result.append(temp)

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="processes receipt file to determine how to split costs among a group")
    parser.add_argument('filename', type=str, help="The name of the file to read")
    args = parser.parse_args()

    try:
        with open(args.filename, 'r') as file:
            lines = [line.rstrip() for line in file]
    except IOError as e:
        raise Exception(f"Error reading file: {e}")

    # Parse header
    names = parse_names(lines[0])
    description = clean_line("DESCRIPTION:", lines[1])
    receipt_data = []

    # Parse each of the receipts
    for receipt_lines in split_list_by_value(lines[2:], "--"):
        receipt_data.append(parse_receipt(receipt_lines, names))
        print_receipt(receipt_data[-1], names)
    
    # Calculate how much each person owes
    money_deltas = calculate_money_deltas(receipt_data, names)
    transactions = calculate_pay_transactions(money_deltas, names)

    print_deltas(money_deltas, names)
    print_transactions(transactions)
    
    print()
    print("*disclaimer*: rounding errors may result in numbers off by a cent or two")
