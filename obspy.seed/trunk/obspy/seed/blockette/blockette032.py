# -*- coding: utf-8 -*-

from obspy.seed.blockette import Blockette 
from obspy.seed.fields import Integer, VariableString


class Blockette032(Blockette):
    """Blockette 032: Cited Source Dictionary Blockette.
        
    This blockette identifies the contributing institution that provides 
    the hypocenter and magnitude information. This blockette is used in event 
    oriented network volumes.
    """
    
    id= 32
    name = "Cited Source Dictionary Blockette"
    fields = [
        Integer(3, "Source lookup code", 2),
        VariableString(4, "Name of publication or author", 1, 70, 'UNLPS'),
        VariableString(5, "Date published or catalog", 1, 70, 'UNLPS'),
        VariableString(6, "Publisher name", 1, 70, 'UNLPS'),
    ]
