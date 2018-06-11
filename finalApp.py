#                                           Bitcoin Demo Trader REST API webapp
########################################################################################################
#CS496 CLOUD AND MOBILE DEVELOPMENT SPRING 2018
#MARK BUCKNER 
#6.10.2018
#3rd party API used https://www.coindesk.com/api/ -- provides Bitcoin ($BTC) Price Index real-time data 
########################################################################################################
import os
import httplib, urllib
import webapp2 # Google App Engine library
import json
import jinja2 # BSD licensed templating engine for python https://en.wikipedia.org/wiki/Jinja_(template_engine)
# I didn't showcase full power of jinja here, but it's good to have implemented in case I want to expand this later with dynamic content 
import random #for state variable
import logging
import string
from oauth2client import client, crypt   #https://github.com/google/oauth2client client to help with handling oauth2 tokens
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext.webapp import template 
########################################################################################################
########################################################################################################
## -- OAuth 
CLIENTID = ""    #Set the variables to use throughout. Client ID and secret are provided when setting up credentials
CLIENTSECRET = ""
AUTHurl = "https://accounts.google.com/o/oauth2/v2/auth"
CALLBACKurl = "http://localhost:8080/callback"    
########################################################################################################
########################################################################################################
#Jinja2 templating engine
#citation: https://cloud.google.com/appengine/docs/standard/python/getting-started/generating-dynamic-content-templates
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),      
    extensions=['jinja2.ext.autoescape'],                                   
    autoescape=True)

class State(ndb.Model):#oauth2 random state variable
    value = ndb.StringProperty(required=True)
########################################################################################################
########################################################################################################
# Helper function for handling oauth2 tokens
def tokenHandler(token):# reference for idinfo values 'iss', 'aud', and 'sub': https://developers.google.com/identity/sign-in/web/backend-auth#calling-the-tokeninfo-endpoint
    if token is not None:
        try:# documentation: http://oauth2client.readthedocs.io/en/latest/source/oauth2client.crypt.html
            idinfo = client.verify_id_token(token, None)
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:#included in all Google ID tokens
                raise crypt.AppIdentityError("Access Denied")
            if idinfo['aud'] not in [CLIENTID]: #Check if client id was correct
                raise crypt.AppIdentityError("Access Denied")
            userid = idinfo['sub']#Grab the unique id
            return userid #This function returns the piece of the unique id we want for a "token"
        except crypt.AppIdentityError:
            return None
    else:
        return None

# Helper function for nonrelational database parent keys    
def findParentKey(userid):
    if userid is not None:
        parent_key = ndb.Key(Trade, repr(userid))
        return parent_key
    else:
        return None
########################################################################################################
########################################################################################################
class OAuthHandler(webapp2.RequestHandler):#Same as in previous assignments...citation: http://classes.engr.oregonstate.edu/eecs/spring2018/cs496/module-4/oauth-demo.html
    def get(self,):
        state_return = self.request.get('state')
        code = self.request.get('code')
        header = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        payload = {#Same as in previous assignments... citation: http://classes.engr.oregonstate.edu/eecs/spring2018/cs496/module-4/oauth-demo.html                                
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': CLIENTID,
        'client_secret': CLIENTSECRET,
        'redirect_uri': CALLBACKurl}
        result = urlfetch.fetch(url='https://www.googleapis.com/oauth2/v4/token', headers=header, payload=urllib.urlencode(payload), method=urlfetch.POST) 
        returning = json.loads(result.content)
        #grab token 
        token = returning['id_token']
        
        tempVars = {
            'accessToken': token
        }
        #Upon a successful login, the app renders a page showing the granted token
        #This token can then be copypasted into the Postman collection variables {{user1}}, {{user2}} for subsequent API calls
        template = JINJA_ENVIRONMENT.get_template('success.html') 
        self.response.write(template.render(tempVars)) 
########################################################################################################
########################################################################################################        
class Person(ndb.Model):                                        
    id = ndb.StringProperty()
    access_header = ndb.StringProperty(required=True)
    username = ndb.StringProperty(required=True)#Accounts will be identified by access header from oauth and username
    email = ndb.StringProperty()#It's not needed to login, but I added this field because email could be useful in future
    btc_value = ndb.FloatProperty()#To track how much BTC the user has    
    usd_value = ndb.FloatProperty()#To track how much USD the user has
        
class PersonHandler(webapp2.RequestHandler):
    def get(self, id=None):
        if 'access_header' in self.request.headers:
            header_data = tokenHandler(self.request.headers['access_header'])#If access header is there, parse token and store unique id in variable
        else:
            self.response.set_status(400)
            self.response.write("Invalid access header.")          #Otherwise tell user they need to put a proper header
            return
        if header_data:
            if id:#If getting a specific user, find them by id and write their values
                person = ndb.Key(urlsafe=id).get()
                if person:
                    if person.access_header == header_data:
                        self.response.set_status(200)
                        person_dict = person.to_dict()
                        person_dict['self'] = "/people/" + person.id
                        self.response.write(json.dumps(person_dict))
                    else:
                        self.response.set_status(403)#Can't access data without the proper header
                        return
                else:
                    self.response.set_status(404)
                    return
            else:#Else, find all the people
                parent_key = findParentKey(header_data)
                people = Person.query(ancestor=parent_key).fetch()
                if people:#Output all people associated with the user (i.e., all people entities created by that user)
                    for p in people:
                        person_dict = p.to_dict()
                        self.response.write(json.dumps(person_dict))  
                else:
                    self.response.set_status(404)
                    self.response.write("No people found.")
                    return
        else:
            self.response.set_status(403)                   #Tell user there is an issue
            self.response.write("Invalid or expired token")
            return
            
    def post(self):
        if 'access_header' in self.request.headers:
            token = self.request.headers['access_header']       #same setup for POST. Get access header and use that to set values
            header_data = tokenHandler(token)
        else:
            self.response.set_status(403)
            self.response.write("Invalid access header.")
            return
        person_data = json.loads(self.request.body)
        if header_data and 'username' in person_data:
            if person_data['username']:                        
                self.response.set_status(201)
                new_person = Person(parent=findParentKey(header_data), access_header=header_data, username=person_data['username'], email = None, btc_value=None, usd_value=None)
                if 'email' in person_data:
                    new_person.email = person_data['email']
                if 'btc_value' in person_data:
                    new_person.btc_value = person_data['btc_value']
                else: 
                    new_person.btc_value = 0.0 #Default to 0 if no value given
                if 'usd_value' in person_data:
                    new_person.usd_value = person_data['usd_value']
                else: 
                    new_person.usd_value = 0.0 #Default to 0 if no value given
                new_person.put()#Create new person in database
                new_person.id = new_person.key.urlsafe()#Create new person id
                new_person.put()#Upate person
                person_dict = new_person.to_dict()#add to dictionary
                person_dict['self'] = "/people/" + new_person.id
                
                self.response.write(json.dumps(person_dict))
                
            else:#Error reporting
                self.response.set_status(400)
                return
        else:
            self.response.set_status(400)
            self.response.write("error")
            return
    
    def patch(self, id=None):
        if id:
            if 'access_header' in self.request.headers:
                header_data = tokenHandler(self.request.headers['access_header'])
            else:
                self.response.set_status(400)
                self.response.write("Invalid access header.")
                return
            person_data = json.loads(self.request.body)
            person = ndb.Key(urlsafe=id).get()
            if person:
                if header_data == person.access_header:#Either update the information or do nothing
                    if 'username' in person_data and person_data['username']:
                        person.username = person_data['username']
                    if 'email' in person_data:
                        person.email = person_data['email']
                    if 'btc_value' in person_data:
                        person.btc_value = person_data['btc_value']
                    if 'usd_value' in person_data:
                        person.usd_value = person_data['usd_value']
                    person.put()
                    self.response.write("User data updated successfully.")#Tracing the program
                else:#Error codes
                    self.response.set_status(403)
            else:
                self.response.set_status(404)
        else:
            self.response.set_status(400)
    
    def put(self, id=None):
        if id:
            if 'access_header' in self.request.headers:
                header_data = tokenHandler(self.request.headers['access_header']) 
            else:
                self.response.set_status(400)
                self.response.write("Invalid access header.")
                return
            person_data = json.loads(self.request.body)
            person = ndb.Key(urlsafe=id).get()
            if person:
                if header_data == person.access_header:#Either update the information or do nothing
                    if 'username' in person_data and person_data['username']:
                        person.username = person_data['username']
                        if 'email' in person_data:
                            person.email = person_data['email']
                        if 'btc_value' in person_data:
                            person.btc_value = person_data['btc_value']
                        if 'usd_value' in person_data:
                            person.usd_value = person_data['usd_value']
                        person.put()
                        self.response.write("User data updated successfully.")#Tracing the program
                    else:
                        self.response.set_status(400)
                        self.resposne.write("Error")
                else:
                    self.response.set_status(403)
            else:
                self.response.set_status(404)
        else:
            self.response.set_status(400)
    
    def delete(self, id=None):
        if id:
            if 'access_header' in self.request.headers:
                header_data = tokenHandler(self.request.headers['access_header'])
            else:
                self.response.set_status(400)
                return
            person = ndb.Key(urlsafe=id).get()
            if person:
                if header_data == person.access_header:
                    TradeFind = Trade.query(Trade.username == id).get()     
                    if TradeFind:                                                               
                        TradeFind.username = None
                        TradeFind.put()#Set trade username to ""
                    self.response.set_status(200)
                    person.key.delete()
                else:
                    self.response.set_status(403)
            else:
                self.response.set_status(404)
                return
        else:
            self.response.set_status(400)
            return
########################################################################################################            
########################################################################################################            
class Trade(ndb.Model):#Class for Bitcoin-USD trades. Required: access header, username, and time_stamp
    id = ndb.StringProperty()
    access_header = ndb.StringProperty(required=True)#OAuth
    username = ndb.StringProperty(required=True)#Who made the trade?
    time_stamp = ndb.StringProperty(required=True)#When was the trade made?
    rate = ndb.FloatProperty(required=True)#BTC price at time of trade
    amount = ndb.FloatProperty()#How much bitcoin is the person buying or selling?
    buying = ndb.BooleanProperty() #TRUE if buying BTC with USD; FALSE if buying USD with BTC (i.e., selling BTC)
    

class TradeHandler(webapp2.RequestHandler):   
    def get(self, id=None):
        if 'access_header' in self.request.headers:
            header_data = tokenHandler(self.request.headers['access_header'])#Same access logic
        else:
            self.response.set_status(400)
            self.response.write("Need proper header")
            return
        if header_data:#Either get a single Trade by ID or get the users Trades
            if id:
                trade = ndb.Key(urlsafe=id).get()
                if trade:
                    if trade.access_header == header_data:
                        self.response.set_status(200)
                        trade_dict = trade.to_dict()
                        trade_dict['self'] = "/trades/" + id
                        self.response.write(json.dumps(trade_dict))
                    else:#Error codes...
                        self.response.set_status(403)
                        return
                else:
                    self.response.set_status(404)
                    return
            else:#if no trade id is given, find all the trades
                parent_key = findParentKey(header_data)
                trades = Trade.query(ancestor=parent_key).fetch()
                if trades:
                    for t in trades:
                        trade_dict = t.to_dict()
                        self.response.write(json.dumps(trade_dict))
                else:#Error codes...
                    self.response.set_status(404)
                    self.response.write("No trades found.")
                    return
        else:
            self.response.set_status(400)#Tell user there is an issue
            self.response.write("header error")
            return
            
    def post(self):
        if 'access_header' in self.request.headers:#Create a new Trade
            token = self.request.headers['access_header']
            header_data = tokenHandler(token)
        else:
            self.response.set_status(403)
            return
        Trade_data = json.loads(self.request.body)
        if header_data and 'username' in Trade_data:
            if Trade_data['username']:
                self.response.set_status(201)
                new_Trade = Trade(parent=findParentKey(header_data),access_header=header_data,username=None, time_stamp=None, rate=None,amount=None,buying=None)
                if 'username' in Trade_data:
                    new_Trade.username = Trade_data['username']
                if 'time_stamp' in Trade_data:
                    new_Trade.time_stamp = Trade_data['time_stamp']
                else:
                    time_result = urlfetch.fetch("https://api.coindesk.com/v1/bpi/currentprice.json")#Im using the coindesk api to grab the current price of bitcoin in USD
                    bpiJSON = json.loads(time_result.content)
                    new_Trade.time_stamp = bpiJSON["time"]["updated"]#Use coindesk price update time for time stamp
                if 'buying' in Trade_data:
                    new_Trade.buying = Trade_data['buying']
                else:
                    new_Trade.buying = True #Default to buying BTC, instead of selling
                if 'rate' in Trade_data:#User can provide a rate when they post a trade; else it will default to coindesk bpi rate
                    new_Trade.rate = Trade_data['rate']
                else:
                    rate_result = urlfetch.fetch("https://api.coindesk.com/v1/bpi/currentprice.json")#grab the current price of bitcoin in USD via condesk API
                    bpiJSON = json.loads(rate_result.content)
                    new_Trade.rate = bpiJSON["bpi"]["USD"]["rate_float"]#default to live price if user didnt provide a rate
                if 'amount' in Trade_data:
                    new_Trade.amount = Trade_data['amount']
                else:
                    new_Trade.amount = 1.0 #default to a trade amount of 1 if we don't have the data from the user
                new_Trade.put()
                new_Trade.id = new_Trade.key.urlsafe()
                new_Trade.put()#Update database
                trade_dict = new_Trade.to_dict()
                trade_dict['self'] = "/trades/" + new_Trade.id
                self.response.write(json.dumps(trade_dict))
            else:
                self.response.set_status(400)
                return
        else:
            self.response.set_status(400)
            return
            
    def patch(self, id=None):#Updates Trade data. 
        if id:
            if 'access_header' in self.request.headers:
                header_data = tokenHandler(self.request.headers['access_header'])
            else:
                self.response.set_status(400)
                return
            Trade_data = json.loads(self.request.body)
            Trade = ndb.Key(urlsafe=id).get()
            if Trade:
                if header_data == Trade.access_header:
                    if 'username' in Trade_data:
                        Trade.username = Trade_data['username']
                    if 'time_stamp' in Trade_data:
                        Trade.time_stamp = Trade_data['time_stamp']
                    if 'buying' in Trade_data:
                        Trade.buying = Trade_data['buying']
                    if 'rate' in Trade_data:
                        Trade.rate = Trade_data['rate']
                    if 'amount' in Trade_data:
                        Trade.amount = Trade_data['amount']
                    Trade.put()
                    self.response.write("Trade data successfully updated.")
                else:
                    self.response.set_status(403)
            else:
                self.response.set_status(404)
                return
        else:
            self.response.set_status(400)
            return
    
    def put(self, id=None):#Replaces Trade data.
        if id:
            if 'access_header' in self.request.headers:
                header_data = tokenHandler(self.request.headers['access_header'])
            else:
                self.response.set_status(400)
                return
            Trade_data = json.loads(self.request.body)
            Trade = ndb.Key(urlsafe=id).get()
            if Trade:
                if header_data == Trade.access_header:
                    if 'username' in Trade_data:
                        Trade.username = Trade_data['username']
                    else:
                        Trade.username = "USERNAME-DEFAULTED"
                    if 'time_stamp' in Trade_data:
                        Trade.time_stamp = Trade_data['time_stamp']
                    else:
                        time_result = urlfetch.fetch("https://api.coindesk.com/v1/bpi/currentprice.json")#Im using the coindesk api to grab the current price of bitcoin in USD
                        bpiJSON = json.loads(time_result.content)
                        Trade.time_stamp = bpiJSON["time"]["updated"]#Use coindesk price update time for time stamp if none provided
                    if 'rate' in Trade_data:
                        Trade.rate = Trade_data['rate']
                    else:
                        rate_result = urlfetch.fetch("https://api.coindesk.com/v1/bpi/currentprice.json")#grab the current price of bitcoin in USD via condesk API
                        bpiJSON = json.loads(rate_result.content)
                        Trade.rate = bpiJSON["bpi"]["USD"]["rate_float"]#default to live price if user didnt provide a rate
                    if 'buying' in Trade_data:
                        Trade.buying = Trade_data['buying']
                    else:
                        Trade.buying = True #Default to buying bitcoin with usd, as opposed to selling
                    if 'amount' in Trade_data:
                        Trade.amount = Trade_data['amount']
                    else:
                        Trade.amount = 1.0 #Defaulted to trade amount of 1 
                    self.response.write("Trade data successfully updated.")
                    Trade.put()
                else:#Error codes...
                    self.response.set_status(403)
            else:
                self.response.set_status(404)
                return
        else:
            self.response.set_status(400)
            return
    
    def delete(self, id=None):#Remove a Trade
        if id:
            if 'access_header' in self.request.headers:
                header_data = tokenHandler(self.request.headers['access_header'])
            else:
                self.response.set_status(400)
                return
            Trade = ndb.Key(urlsafe=id).get()
            if Trade:
                if header_data == Trade.access_header:
                    Trade.key.delete()#Delete the entity from db
                else:#Error codes..
                    self.response.set_status(403)
            else:
                self.response.set_status(404)
                return
        else:
            self.response.set_status(400)
            return
########################################################################################################
########################################################################################################
########################################################################################################
########################################################################################################
########################################################################################################
########################################################################################################            
    
class MainPage(webapp2.RequestHandler):         
    def get(self):
        random_state = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])#Use random state var to prevent XSRF attacks
        new_state = State(value=random_state)
        new_state.put()
        url = AUTHurl + "?response_type=code&client_id=" + CLIENTID + "&redirect_uri=http://localhost:8080/callback" + "&scope=email&state=" + random_state  
        result = urlfetch.fetch("https://api.coindesk.com/v1/bpi/currentprice.json")#Im using the coindesk api to grab the current price of bitcoin in USD
        bpiJSON = json.loads(result.content)#bpi is 'bitcoin price index'
        btcprice = bpiJSON["bpi"]["USD"]["rate_float"]
        disclaimer = bpiJSON["disclaimer"]#Tells that the data is from Coindesk
        #template engine vars
        tempVars = {
            'signin': url,
            'btcprice': btcprice,
            'disclaimer': disclaimer
        }
        #sign in button link has oauth url including clientid and random state variable
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(tempVars))        


#Next 3 lines allow the patch method in webapp2
allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods
########################################################################################################
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/callback', OAuthHandler),
    ('/people', PersonHandler),# first entity is People
    ('/people/(.*)', PersonHandler),
    ('/trades', TradeHandler),# second entity is Trades
    ('/trades/(.*)', TradeHandler),    
], debug=True)
########################################################################################################
#EOF



