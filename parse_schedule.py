from html.parser import HTMLParser
import urllib.request as urllib2
import json

# loads in the class infomation from the CMU schedule found at 
# https://enr-apps.as.cmu.edu/assets/SOC/sched_layout_spring.htm
"""
The conventions used on the page are as follows:
    * each row is a <tr> element
    * each column within the row is a <td> element
    * each row contains a reciation section and/or general class information
    * a row containing class information is followed by recitaion sections, if they exist
    * each column contains one piece of infomation, conistant across rows
    * empty columns contain one space character
"""
class cmuClassScheduleParser(HTMLParser):

    in_tr = False
    ind = 0
    this_class = {}
    classes = {}
    classes['topics'] = []
    this_section = ''
    get_section = False

    def handle_starttag(self, startTag, attrs):
        if startTag == 'tr':
            self.in_tr = True
        if startTag == 'b':
            self.in_tr = False
            self.get_section = True

    def handle_endtag(self, endTag):
        if endTag == 'tr':
            self.in_tr = False
            self.ind = 0
        if endTag == 'b':
            self.get_section = False

    def handle_data(self, data):
        if self.in_tr:
            # print(data)
            if self.ind == 0:
                if not data.isspace():
                    # we have a new class 
                    if 'num' in self.this_class:
                        # add the old class to the list of classes under the course number
                        self.classes[self.this_class['num']] = self.this_class

                    # start a new class 
                    self.this_class = {} 
                    # add the course number
                    self.this_class['num'] = data
                    self.this_class['dept'] = self.this_section
                    self.this_class['sections'] = []

            elif self.ind == 1:
                if not data.isspace():
                    # we have a new classes' title 
                    self.this_class['name'] = data
   
            elif self.ind == 2:
                if not data.isspace():
                    # we have a new classes' unit count
                    self.this_class['units'] = data

            elif self.ind == 3:
                # we have a section
                self.this_class['sections'].append({'num': data})

            elif self.ind == 4:
                # we have a day/days
                self.this_class['sections'][-1]['day'] = data

            elif self.ind == 5:
                # we have a start time
                self.this_class['sections'][-1]['start'] = data

            elif self.ind == 6:
                # we have an end time
                self.this_class['sections'][-1]['end'] = data

            elif self.ind == 7:
                # we have a room
                self.this_class['sections'][-1]['room'] = data

            elif self.ind == 8:
                # we have a place
                self.this_class['place'] = data

            elif self.ind == 9:
                # we have a prof
                self.this_class['sections'][-1]['instructor'] = data

            self.ind += 1

        elif self.get_section:
            self.classes['topics'].append(data)
            self.this_section = data

# create a parser object 
parser = cmuClassScheduleParser()

print("Loading schedule...")
# load the html page
html_page = html_page = urllib2.urlopen("https://enr-apps.as.cmu.edu/assets/SOC/sched_layout_spring.htm")
print("Parsing schedule...")
# parse 
parser.feed(str(html_page.read()))
print("Saving parsed schedule as json")
# save json file
with open('spring2019classes.json', 'w') as outfile:
        json.dump(parser.classes, outfile)
print("Success!")