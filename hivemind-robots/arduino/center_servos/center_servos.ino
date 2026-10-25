#include <Servo.h>
Servo base, lift, claw;
void setup(){ base.attach(9); lift.attach(10); claw.attach(11); base.write(90); lift.write(90); claw.write(90); }
void loop(){}
