import yaml
import os

class Consts:
    # Channels
    dAddr = 'Dev4'
    pdChan = 'ai2'
    pdTChan = 'ai4'
    tpChan = 'ai1'
    tpTChan = 'ai3'

    # Plot Settings
    binSize = '1'
    sampFreq = '2000'
    pWindow = '1'

    # Save Settings
    sPeriod = '10'
    sAvg = 'True'
    sLoc = '.'

    def get(self):
        r = [self.dAddr, self.pdChan, self.pdTChan, self.tpChan, self.tpTChan, self.binSize, self.sampFreq, self.pWindow, self.sPeriod, self.sAvg, self.sLoc]
        return r
    
class Cfg(Consts):
    filename = 'settings.yml'

    def createDefault(self):
        """ Create default config file """
        self.set(['Dev4','ai1','ai3','ai0','ai4','10','2000','1','10','False','.'])
        # self.settings = yaml.safe_load(inp)
        with open(self.filename, 'w') as file:
            yaml.dump(self.settings, file)
        return None
    
    def exists(self):
        """ Check if config file exists """
        if os.path.isfile(self.filename):
            return True
        else:
            return False

    def get2(self):
        self.dAddr = self.settings['daq']['chan']
        self.pdChan = self.settings['daq']['pdChan']
        self.pdTChan = self.settings['daq']['pdTempChan']
        self.tpChan = self.settings['daq']['thermoChan']
        self.tpTChan = self.settings['daq']['thermoTempChan']

        self.binSize = self.settings['aqc']['bin']
        self.sampFreq = self.settings['aqc']['freq']
        self.pWindow = self.settings['aqc']['window']

        self.sPeriod = self.settings['save']['per']
        self.sAvg = self.settings['save']['avg']
        self.sLoc = self.settings['save']['loc']
        return None

    def loadCfg(self):
        """ Load config file """
        if(self.exists()):
            with open(self.filename, 'r') as file:
                self.settings = yaml.safe_load(file)
        else:
            self.createDefault()
        self.get2()
        return None

    def set(self, s):
        """ Create config file object """
        inp = """\
        daq:
            chan: {}
            pdChan: {}
            thermoChan: {}
            pdTempChan: {}
            thermoTempChan: {}
        aqc:
            bin: {}
            freq: {}
            window: {}
        save:
            per: {}
            avg: {}
            loc: {}
        """.format(s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9], s[10])
        self.settings = yaml.safe_load(inp)
        return None

    def saveCfg(self):
        """ Save config file to file """
        with open(self.filename, 'w') as file:
            yaml.dump(self.settings, file)

        # print(open(self.filename).read())
        return None

    def print(self):
        print(self.settings)
        return None
    
if __name__=="__main__":
    a = Cfg()
    a.createDefault()
    print(a.settings)
    a.saveCfg()