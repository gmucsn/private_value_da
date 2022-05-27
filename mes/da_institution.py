from mTree.microeconomic_system.environment import Environment
from mTree.microeconomic_system.institution import Institution
from mTree.microeconomic_system.agent import Agent
from mTree.microeconomic_system.directive_decorators import *
from mTree.microeconomic_system.message import Message
import math
import random
import logging
import time
import datetime


@directive_enabled_class
class DAInstitution(Institution):
    """
    DA Institution runs the double_auction institution using an 
    improvement rule on standing_bid and standing_ask to make contracts
    for one unit each.  Order history is maintained in the order_book.
    """  
    def __init__(self):
        pass


    def send_message(self, directive, receiver, payload, use_env = False):
        """Sends message to receiver
           use_env = True has method use environment address """
        new_message = Message()
        new_message.set_sender(self.myAddress)
        new_message.set_directive(directive)
        new_message.set_payload(payload)
        if use_env:
            receiver = "Environment"
            receiver_address = self.environment_address
        else:
            receiver_address = self.address_book.select_addresses(
                               {"short_name": receiver})
        self.log_message(
            f"..<M>..Message {directive} from Institution sent to {receiver}") 
        self.send(receiver_address, new_message)


    @directive_decorator("init_institution")
    def init_institution(self, message: Message):
        """
        Behavior: Initializes institution with starting state
        Receives: init_institution message with payload equal to opening state. 
        Sends: institution_confirm_init message to environment.
        Sets: payload in state dictionary
            : environment address in self.environment_address 
            : True in auction_closed
        """
        self.environment_address = message.get_sender()
        self.auction_closed = True
        self.order_book = []
        self.state = message.get_payload()
        self.send_message("institution_confirm_init", "Environment", None, True)
 

    def process_order(self, order_type, agent, order_value, status):
        """Puts order in order_book"""
        order_entry = {}
        order_entry['time']= time.time()
        order_entry['agent'] = agent
        order_entry['status'] = status
        order_entry['order_type'] = order_type
        order_entry['order_value'] = order_value
        self.order_book.append(order_entry)


    def init_standing(self):
        """initializes stabding bid and ask to starting bid and ask"""
        self.standing_bid = self.state["starting_bid"]
        self.standing_ask = self.state["starting_ask"]
        self.process_order("BID", self.short_name, self.standing_bid, "update_standing_bid")
        self.process_order("ASK", self.short_name, self.standing_ask, "update_standing_ask")
 

    @directive_decorator("open_institution")
    def open_institution(self, message: Message):
        """
        Behavior: opens institution and informs agents
        Receives: open_institution message with payload equal agent address book. 
        Sends: institution_open message to agents.
        Initializes: order_book a list of orders
                     contracts a list of contracts
        """
        self.address_book.merge_addresses(message.get_payload())
        self.log_message(f'<I> {self.address_book.get_addresses()}')
        self.order_book = []
        self.contracts = []
        self.init_standing()
        self.auction_closed = False
        for agent in self.address_book.get_addresses():
            self.send_message("double_auction_open", agent, None, False) 
 

    @directive_decorator("request_standing")
    def request_standing(self, message: Message):
        """
        Tells: agent standing_bid and standing_ask
        Receives: request_staning message.  Payload = agents short_name 
        Sends: standing message to requesting agent
        """
        if self.auction_closed: return
        agent = message.get_payload() #saves the agent address 
        payload = (self.standing_bid, self.standing_ask) 
        self.send_message('standing', agent, payload, False)


    def process_contract(self, buyer_id, seller_id, price):
        contract = (buyer_id, seller_id, price)
        self.process_order("CONTRACT", self.short_name, contract, "contract")
        self.contracts.append(contract)
        self.send_message('contract', 'environment', contract, True)       
 

    def process_bid(self, agent_order):
        bid = agent_order['order_value']
        bidder = agent_order['agent']
        if bid >= self.standing_ask:
            status = 'contract'
            self.process_contract(bidder, self.standing_ask_id, self.standing_ask)
        elif bid > self.standing_bid:
            status = "update_standing_bid"
            self.standing_bid = bid
            self.standing_bid_id = bidder
            self.process_order("BID", self.standing_bid_id, 
                               self.standing_bid, "update_standing_bid")
        else:
            status = "no improvement"
            self.process_order("BID", bidder, 
                               bid, "no_improvement")
        self.log_data(f'<I>: {bidder} BID {bid}: STATUS {status}')
        if status != 'contract':
            self.log_data(f'<I>: STANDING = {self.standing_bid}, {self.standing_ask}')
        else:
            self.log_data(f'<I>: CONTRACT = {self.contracts[-1]}')
            self.log_data(f'<I>: RESET = {self.state["starting_bid"]}, {self.state["starting_ask"]}')

   
    def process_ask(self, agent_order):
        ask = agent_order['order_value']
        asker = agent_order['agent']
        if ask <= self.standing_bid:
            status = 'contract'
            self.process_contract(self.standing_bid_id, asker, self.standing_bid)
        elif ask < self.standing_ask:
            status = "update_standing_ask"
            self.standing_ask = ask
            self.standing_ask_id = asker
            self.process_order("ASK", self.standing_ask_id, 
                               self.standing_ask, "update_standing_ask")
        else:
            status = "no improvement"
            self.process_order("ask", asker, 
                               ask, "no_improvement")
        self.log_data(f'<I>: {asker} ASK {ask}: STATUS {status}')
        if status != 'contract':
            self.log_data(f'<I>: STANDING = {self.standing_bid}, {self.standing_ask}')
        else:
            self.log_data(f'<I>: CONTRACT = {self.contracts[-1]}')
            self.log_data(f'<I>: RESET = {self.state["starting_bid"]}, {self.state["starting_ask"]}')


    @directive_decorator("order")
    def order(self, message: Message):
        """
        Process: order from agent
        Receives: order with payload equal to order. 
        Calls: process_bid or process_ask depending on order_type 
        Sends: order_processed message to agent with payload = revised_order
        """
        if self.auction_closed: return
        agent_order = message.get_payload() #saves the agent order
        self.log_message(f".... ORDER..{agent_order}")  
        if agent_order['order_type'] == "BID":
            self.process_bid(agent_order)
        elif agent_order['order_type'] == "ASK":
            self.process_ask(agent_order)
        else:
            pass
        revised_order = self.order_book[-1]
        self.log_message(f'<I> revised_order {revised_order}')
        if revised_order['order_type'] == 'CONTRACT':
            buying_agent = revised_order['order_value'][0]
            selling_agent = revised_order['order_value'][1]
            self.send_message('order_processed', buying_agent, revised_order, False)
            self.send_message('order_processed', selling_agent, revised_order, False)
            self.init_standing()
        else:
            self.send_message('order_processed', agent_order['agent'], revised_order, False)

 
    @directive_decorator("close_institution")
    def close_institution(self, message: Message):
        """
        Close: double_auction institution
        Receives: close_double_auction from environment
        Sends: double_auction_closed message to agents
        Saves: order_book in message log
        Sets: auction_closed = True
        """
        self.log_message(f'>>>>> ORDER BOOK >> {self.order_book}')
        self.auction_closed = True
        self.log_message(f"<I>... address_book, {self.address_book.get_addresses()}")
        for agent in self.address_book.get_addresses():
            self.send_message("double_auction_closed", agent, None, False) 
