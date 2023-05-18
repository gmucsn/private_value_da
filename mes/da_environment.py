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
class DAEnvironment(Environment):
    """
    The DA environment initializes the agents and the institutions using
    specific control variables in the config.  The environment is 
    responsible for sending the init messages to the agents and institution,
    and openming and closing the exchange.                  
    
 
    Messages Received:
    - start_environment, sent by mTree_runner
    - env_end_period, sent by self
    - agent_confirm_init, sent by BasicAgents
    - institution_confirm_init, sent by DAInstitution
    - request_contracts, sent by BasicAgents
    - contract, sent by DAInstitution


    Messages Sent
    - init_institution, payload = data_dict
    - init_agents, payload = agent_dict
    - start_exchange, payload = None
    - end_exchange, payload = None
    - contracts, payload = contract_list
    """

    def prepare(self):
        self.log_message("<E> prepare")    
        self.endowment = self.get_property("endowment")
        self.values = self.get_property("values") # list of lists 
        self.costs = self.get_property("costs")
        self.starting_bid = self.get_property("starting_bid")
        self.starting_ask = self.get_property("starting_ask")
        self.processing_fee = self.get_property("processing_fee")
        self.period_length = self.get_property("period_length")
        self.number_of_periods = self.get_property("number_of_periods")
        self.agents_ready = None
        self.contracts = []

        self.num_buyers = len(self.values)
        self.num_sellers = len(self.costs)
        self.num_agents = self.num_buyers + self.num_sellers
        self.agent_data = {}
        for k in range(self.num_agents):
            name = f"da_agent.BasicAgent {k+1}"
            if k < self.num_buyers:
                self.agent_data[name] = {"id": k,
                     "role": "Buyer",
                     "endowment": self.endowment,
                     "values_or_costs": self.values[k],
                     "name": name}
            else: 
                self.agent_data[name] = {"id": k-self.num_buyers,
                     "role": "Seller",
                     "endowment": self.endowment,
                     "values_or_costs": self.costs[k-self.num_buyers],
                     "name": name}

        self.log_message(f"<E> prepare {self.agent_data}")


    def set_reminder(self, directive, seconds_to_reminder):
        """Sets a reminder to send a message"""
        reminder_msg = Message()    
        reminder_msg.set_sender(self.myAddress)
        reminder_msg.set_directive(directive)
        self.reminder(seconds_to_reminder = seconds_to_reminder,
                      message = reminder_msg)
        

    @directive_decorator("start_environment")
    def start_environment(self, message: Message):
        """
        Behavior: Initializes institution with starting bid and starting ask
        Receives: start_environment message from mTree 
        Sends: init_institution message to institution with institution payload 
        Calls: init_environment
             : set_reminder
        """
        self.set_reminder('env_end_period', 60)
        payload = {'starting_bid': self.starting_bid, 'starting_ask': self.starting_ask}
        self.send_message("init_institution", "da_institution.DAInstitution", payload)


    @directive_decorator("institution_confirm_init")
    def institution_confirm_init(self, message:Message):
        """
        Behavior: Initializes agents with values and costs
        Receives: 'institution_confirm_init' message from institution 
        Sends: 'init_agent' message to agents 
        Sets: agents_ready = 0
        """       
        self.agents_ready = 0
        for agent_name, agent in self.agent_data.items():
            self.send_message('init_agent', agent_name, agent)
           

    @directive_decorator("agent_confirm_init")
    def agent_confirm_init(self, message:Message):
        """
        Behavior: Opens institution after agents confirm init
        Receives: 'agent_confirm_init' message from agents
        Waits: for all agents to confirm  
        Sends: 'open_institution' message to institution with address book of agents 
        """
        self.agents_ready += 1
        self.log_message(f"{message}", target=self.short_name)
        self.log_message(f"{self.agents_ready, self.num_agents}", target=self.short_name)
        if self.agents_ready == self.num_agents:
            self.agents_ready = 0
            payload = list(self.agent_data.keys())
            self.log_message(f"agents = {payload}", target=self.short_name)
            self.send_message("open_institution", 'da_institution.DAInstitution', payload) 


    @directive_decorator("contract")
    def contract(self, message:Message):
        """
        Behavior: Saves contract in contracts
        Receives: contract message from instituion
         """
        contract = message.get_payload()
        self.contracts.append(contract)


    @directive_decorator("env_end_period")
    def env_end_period(self, message:Message):
        """
        Behavior: Closes institution for this period
        Receives: env_end_period message from reminder 
        Sends: close_institution message to institution
        Calls:  reminder to close with close_mes message 
        """
        self.send_message("close_institution", 'da_institution.DAInstitution') 
        self.set_reminder('close_mes', 10)


    @directive_decorator("close_mes")
    def close_mes(self, message:Message):
        """
        Behavior: Shuts down the MES
        Receives: close_mes message from reminder 
        Logs: contracts to message log
        Logs: contracts to data log
        Calls: shutdown_mes() 
        """
        self.log_message(">>>>> CLOSE MES >>")
        for k, contract in enumerate(self.contracts):
            self.log_message(contract)
            self.log_data(f'<E>: CONTRACT {k}: {contract}')
        self.log_message(">>>>> END MES RUN >>")
        self.log_data(">>>>> END MES RUN >>")
        self.shutdown_mes()
