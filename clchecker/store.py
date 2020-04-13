import pymongo
import collections
import re
import logging
import config as config

logger = logging.getLogger(__name__)


class Command:
    def __init__(self, command_name, tx_syntax, clsname_to_readable_syntax, concrete_specs, explantion, eman):
        self.command_name = command_name
        self.tx_syntax = tx_syntax
        self.clsname_to_readable_syntax = clsname_to_readable_syntax
        self.concrete_specs = concrete_specs
        self.explanation = explantion
        self.eman = eman

    @classmethod
    def from_store(cls, doc):
        return cls(doc['command_name'], doc['tx_syntax'], doc['clsname_to_readable_syntax'], doc['concrete_specs'], doc['explanation'], doc['eman'])

    def to_store(self):
        return {'command_name': self.command_name, 'tx_syntax': self.tx_syntax, 'clsname_to_readable_syntax': self.clsname_to_readable_syntax, 'concrete_specs': self.concrete_specs, "explanation": self.explanation, 'eman': self.eman}


class Store():
    '''read/write from/to mongodb'''

    def __init__(self, db='clchecker', host=config.MONGO_URI):
        logger.info('creating store, db = %r, host = %r', db, host)
        self.connection = pymongo.MongoClient(host)
        self.db = self.connection[db]
        self.commands = self.db['commands']
        self.commands.create_index([('command_name', 'text')])

    def close(self):
        self.connection.disconnect()
        self.commands = None
        self.command_to_id = None

    def drop_collection(self, confirm=False):
        if not confirm:
            logger.warning('fail to delete collection since confirm is False')
            return

        logger.info('dropping commands collection')
        self.commands.drop()

    def delete_all_documents(self, confirm=False):
        if not confirm:
            logger.warning(
                'fail to delete ALL documents since confirm is False')
            return

        self.commands.delete_many({})
        logger.info('delete all documents in commands collection')

    def delete_document(self, command_name, confirm):
        if not confirm:
            logger.warning(
                f'fail to delete command {command_name} since confirm is False')
            return

        logger.info(f'delete command {command_name} in the database')
        self.commands.delete_one({"command_name": command_name})

    def __contains__(self, command_name):
        c = self.commands.find({'command_name': command_name}).count()
        return c > 0

    def __iter__(self):
        for d in self.commands.find():
            yield Command.from_store(d)

    def findcommand(self, command_name):
        '''find a command document by its name'''
        doc = self.commands.find_one({'command_name': command_name})
        if doc:
            command = Command.from_store(doc)
            return command

    def addcommand(self, command, overwrite=False):
        if self.findcommand(command.command_name) is not None:
            if not overwrite:
                raise ValueError(
                    f'command "{command.command_name}" is already in the database')
            else:
                logger.warning(f'overwrite command {command.command_name}')
                self.commands.replace_one(
                    {'command_name': command.command_name}, command.to_store())
        else:
            self.commands.insert_one(command.to_store())
