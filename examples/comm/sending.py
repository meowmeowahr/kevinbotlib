import time

from kevinbotlib.comm import KevinbotCommInstance, SubTopic, BooleanData, IntegerData, StringData, FloatData

instance = KevinbotCommInstance()

instance.send("demo-boolean", BooleanData(title="Demo Boolean", value=False))
instance.send("demo-int", IntegerData(title="Demo Integer", value=184))
instance.send("demo-str", StringData(title="Demo String", value="System OK"))

sub = SubTopic(instance, "demo-subtopic")
sub.send("demo-float", FloatData(title="Demo Float", value=3.14))

time.sleep(2)

# Clean up
instance.close()