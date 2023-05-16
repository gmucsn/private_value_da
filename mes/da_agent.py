from tkinter.filedialog import askdirectory
from mTree.microeconomic_system.environment import Environment
from mTree.microeconomic_system.institution import Institution
from mTree.microeconomic_system.agent import Agent
from mTree.microeconomic_system.directive_decorators import *
from mTree.microeconomic_system.message import Message
import importlib
import math
import random
import logging
import time
import datetime

@directive_enabled_class
class BasicAgent(Agent):
    """
    Basic Test Agent class for the Microeconomic System.
    The Basic Agent class establishes a message framework to interact 
    with other institutions and accepts different strategies that 
    can be programmed to engage in varying behavior. 
    
    For more details on messages sent and received,
    see method docstrings. 

    Messages Received: 
    - init_agents, sent by DAEnvironment
    - start_exchange, sent by 

    Messages Sent
    """ 

    def set_reminder(self, directive, seconds_to_reminder):
        """Sets a reminder to send a message"""
        reminder_msg = Message()
        reminder_msg.set_sender(self.myAddress)
        reminder_msg.set_directive(directive)
        self.reminder(seconds_to_reminder = seconds_to_reminder,
                      message = reminder_msg)


    @directive_decorator("init_agent")
    def init_agent(self, message: Message):
        """
        Behavior: Initializes agent
        Receives: init_agents message from environment with agent_state payload
        Sends: agent_confirm_init to environment
        Initializes: agent_state["current_unit"] = 0
        Sets: environment_short_name
        Logs: agent_state to message log
        Logs: agent_state to data log 
        """
        self.environment_address = message.get_sender() #saves the environment address 
        self.agent_state = message.get_payload()
        self.agent_state["current_unit"] = 0
        self.send_message('agent_confirm_init', 'da_environment.DAEnvironment')
        
        self.double_auction_closed = True
        self.log_message(f'<A> {self.short_name} = {self.agent_state}')
        agent_role = self.agent_state["role"]
        v_c = self.agent_state["values_or_costs"]
        self.log_data(f'<A>: {self.short_name}: {agent_role}: {v_c}')

    @directive_decorator("double_auction_open")
    def double_auction_open(self, message: Message):
        """
        Behavior: Informs agents auction is open
        Receives: double_auction_open message from institution
        Sends: request_standing to institution
        Initializes: agent_state["current_unit"] = 0
        Sets: environment_short_name
        """
        self.institution_address = message.get_sender()
        self.double_auction_closed = False
        self.set_reminder('make_order', 5)
        self.send_message('request_standing','da_institution.DAInstitution', self.short_name)
        
 
    @directive_decorator("make_order")
    def make_order(self, message: Message):
        """
        Behavior: makes new order
        Receives: make_offer message from self reminder
        Sends: request_standing to institution
        """
        if self.double_auction_closed: return
        self.send_message('request_standing', 'da_institution.DAInstitution', self.short_name)
        

    @directive_decorator("standing")
    def standing(self, message: Message):
        """
        Behavior: Makes bid or ask depending on type
        Receives: standing message from institution with standing_bid and standing_ask
        Calls: make_bid() or make_ask()
        """
        current_standing = message.get_payload()
        self.standing_bid = current_standing[0]
        self.standing_ask = current_standing[1]
        self.log_message(f'<A> in standing current_standing = {current_standing}')
        agent_type = self.agent_state["role"]
        self.log_message(f'<A> in standing agent_type = {agent_type}')
        if agent_type == "Buyer":
            self.make_bid()
        else:
            self.make_ask()
        
        self.set_reminder('make_order', 5)
        

    def make_bid(self): 
        """
        Behavior: Makes a bid if it still has units to buy
        Sends: order message to institution
        Makes: order
        """
        self.log_message(f'<A> Entered make_bid method')
        unit = self.agent_state['current_unit']
        values = self.agent_state['values_or_costs']
        self.log_message(f'<A> in make_bid unit = {unit}')
        if unit < len(values):
            value = values[unit]
            self.log_message(f'<A> in make_bid value = {value}')       
            if value > self.standing_bid:
                bid = random.randint(self.standing_bid, value)
                order ={}
                order['agent'] = self.short_name
                order['order_type'] = "BID"
                order['order_value'] = bid
                #self.log_data(f'<A> {self.short_name} BID {bid} : {value}, {self.standing_bid}')
                self.send_message('order', 'da_institution.DAInstitution', order)


    def make_ask(self): 
        """
        Behavior: Makes a bid if it still has units to buy
        Sends: order message to institution
        Makes: order
        """
        self.log_message(f'<A> Entered make_ask method')
        unit = self.agent_state['current_unit']
        costs = self.agent_state['values_or_costs']
        self.log_message(f'<A> in make_ask unit = {unit}')
        if unit < len(costs):
            cost = costs[unit]
            self.log_message(f'<A> in make_ask cost = {cost}')
            if cost < self.standing_ask:
                ask = random.randint(cost, self.standing_ask)
                order ={}
                order['agent'] = self.short_name
                order['order_type'] = "ASK"
                order['order_value'] = ask
                #self.log_data(f'<A> {self.short_name} ASK {ask} : {cost}, {self.standing_ask}')
                self.send_message('order', 'da_institution.DAInstitution', order)

 
    @directive_decorator("order_processed")
    def order_processed(self, message: Message):
        """
        Behavior: If contract increment current_unit
        Receives: order_processed message from institution with revised order
        """
        payload = message.get_payload()
        if payload['status'] == 'contract':
            self.agent_state["current_unit"] += 1


    @directive_decorator("double_auction_closed")
    def double_auction_closed(self, message: Message):
        """
        Behavior: Stops agent from making new bids
        Receives: double_auction_closed message from institution
        """
        self.double_auction_closed = True