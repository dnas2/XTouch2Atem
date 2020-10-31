from lib.atem import Atem
from lib.xtouch import Xtouch
import config 


print("Starting xtouch2atem")
atem = Atem(config.address)
print("Connecting to Atem on " + config.address)
xtouch = Xtouch(atem)

print (atem.isConnected)
print (xtouch.isConnected)

