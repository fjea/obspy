# -*- coding: utf-8 -*-

from lxml.etree import Element, SubElement
from StringIO import StringIO

from obspy.seed import blockette, utils


CONTINUE_FROM_LAST_RECORD = '*'

HEADERS = ['V', 'A', 'S']
# @see: http://www.iris.edu/manuals/SEEDManual_V2.4.pdf, p. 22-24
HEADER_INFO = {
    'V': {'name': 'Volume Index Control Headers', 
          'blockettes': [10, 11, 12]},
    'A': {'name': 'Abbreviation Dictionary Control Headers', 
          'blockettes': [30, 31, 32, 33, 34, 41, 43, 44, 45, 46, 47, 48]},
    'S': {'name': 'Station Control Headers', 
          'blockettes': [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61]}
}


class SEEDParserException(Exception):
    pass


class SEEDParser:
    """The SEED parser class parses dataless or full SEED volumes.
    
    The SEED file format description can be found at
    @see: http://www.iris.edu/manuals/SEEDManual_V2.4.pdf
    """ 
    
    def __init__(self, filename, verify=True, debug=False, strict=False):
        self.record_length = 4096
        self.version = None
        self.filename = filename
        self.blockettes = {}
        self.debug = debug
        self.verify = verify
        self.strict = strict
        self.fp = open(filename)
        self.doc = Element("DatalessSEEDXML")
        if self.debug:
            print 'FILENAME:', filename
        self.parse()
    
    def __del__(self):
        self.fp.close()
    
    def parse(self):
        """Parses through a whole SEED volume."""
        self.fp.seek(0)
        # retrieve some basic date, like version and record_length
        data = self.fp.read(8)
        if data!='000001V ':
            raise SEEDParserException("Expecting 000001V ")
        # B010 F01
        data = self.fp.read(3)
        if data!='010':
            raise SEEDParserException("Expecting blockette 010")
        # F02
        data = self.fp.read(4)
        # F03
        self.version = float(self.fp.read(4))
        # F04
        length = pow(2,int(self.fp.read(2))) 
        # test record length
        self.fp.seek(length)
        data = self.fp.read(6)
        if data!='000002':
            raise SEEDParserException("Got an invalid logical record " + \
                                      "length %d" % length)
        self.record_length = length
        if self.debug:
            print "RECORD LENGTH:",self.record_length
        # jump back to beginning
        self.fp.seek(0)
        record = self.fp.read(self.record_length)
        data = ''
        record_type = None
        record_id = None
        # loop through file
        while record:
            record_continuation = record[7] == CONTINUE_FROM_LAST_RECORD
            if record_continuation :
                # continued record
                data+=record[8:]
            else:
                self._parseData(data, record_type, record_id)
                # first or new type of record
                record_type = record[6]
                record_id = int(record[0:6])
                data=record[8:]
                if record_type not in HEADERS:
                    # only parse headers, no data
                    break
            if self.debug:
                if not record_continuation:
                    print "========"
                print record[0:8]
            record = self.fp.read(self.record_length)
        self._parseData(data, record_type, record_id)
        # additional verification after parsing whole volume
        if self.verify:
            self._verifyData()
    
    def _parseData(self, data, record_type, record_id):
        """Read and process data of combined records.
        
        Volume index control headers precede all data. Their primary purpose
        is to provide a directory to differentiate parts of the volume for 
        network and event distributions. Only field station volumes use Field 
        Volume Identifier Blockette [5].
        
        Dictionary records let you use abbreviations to refer to lengthy 
        descriptions without having to create external tables. Blockettes [43] 
        through [48] help reduce the amount of space used to specify intricate 
        channel responses in that you can write out the responses once, and 
        refer to them with short lookup codes, thereby eliminating the need to 
        repeat the same information; they are almost identical to blockettes 
        [53] through [58], but differ only in that they are set up for use as 
        response dictionary entries. Use them with the Response Reference 
        Blockette [60].
        
        The station header records contain all the configuration and 
        identification information for the station and all its instruments.
        The SEED format provides a great deal of flexibility for associating 
        recording channels to the station, including the ability to support 
        different data formats dynamically. For each new station, start a new 
        logical record, set the remainder of any previous header records to 
        blanks, and write it out.
        For analog cascading, use the Response (Poles & Zeros) Blockette [53], 
        and the Channel Sensitivity/Gain Blockette [58] if needed. For digital 
        cascading, use the Response (Coefficients) Blockette [54], and the 
        Decimation Blockette [57] or Channel Sensitivity/Gain Blockette [58] 
        if needed. For additional documentation, you may also use the Response 
        List Blockette [55] or the Generic Response Blockette [56].
        """
        data = StringIO(data)
        if not data:
            return
        if record_type not in HEADERS:
            return
        blockette_length = 0
        blockette_id = -1
        
        root = SubElement(self.doc, 
                          utils.toXMLTag(HEADER_INFO[record_type].get('name')))
        
        while blockette_id != 0:
            try:
                blockette_id = int(data.read(3))
                blockette_length = int(data.read(4))
            except:
                break
            if blockette_id==32:
                print self.filename
                import pdb;pdb.set_trace()
                pass
            data.seek(-7, 1)
            if blockette_id in HEADER_INFO[record_type].get('blockettes', []):
                class_name = 'Blockette%03d' % blockette_id
                if not hasattr(blockette, class_name):
                    raise SEEDParserException('Blockette %d not implemented!' %
                                              blockette_id)
                blockette_class = getattr(blockette, class_name)
                blockette_obj = blockette_class(debug = self.debug,
                                                verify = self.verify,
                                                strict = self.strict,
                                                version = self.version,
                                                record_type = record_type,
                                                record_id = record_id)
                blockette_obj.parse(data, blockette_length)
                root.append(blockette_obj.getXML())
                self.blockettes.setdefault(blockette_id, []).append(blockette_obj)
            elif blockette_id != 0:
                raise SEEDParserException("Unknown blockette type %d " + \
                                          "found" % blockette_id)
    
    def _verifyData(self):
        """Parses through all defined blockettes verfication methods."""
        for (id, blockette_objs) in self.blockettes.iteritems():
            for blockette_obj in blockette_objs:
                if hasattr(blockette_obj, 'verifyData'):
                    blockette_obj.verifyData(self)
    
    def getXML(self):
        """Returns a XML representation of all headers of a SEED volume."""
        return self.doc
