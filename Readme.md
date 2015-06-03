# Introduction

# What is SimpleScratchExtension?

SimpleScratchExtension is a python framework to help  writing 
[scratch HTTP extension](http://wiki.scratch.mit.edu/wiki/Scratch_Extension#HTTP_Extensions). The goals are:

- Hide http protocol
- Focus work on write just components business code

The main class of the framework is `scratch.extension.Extension`. `Extension` use components from `scratch.components` 
that represent scratch extension blocks. To build an extension you should just extend `Extension` class and implement
`do_init_components()` that should return the components list. The http service for scratch communication is provided by
 `scratch.extension.ExtensionService` object that take an extension and service http requests.
 
# Code Structure

# Tests
 
# First Example: set sprite position
 
A simple example is the simplest way to explain the framework philosophy. The complete (and runnable) code is 
[first.py](example/first.py) but now we will focus our attentions on the key parts:

 1. Extension class
 2. Component creation
 3. Interact with components
 4. Service start
 5. Description file saving

In this extension we create a single value reporter block (AKA *sensor*: the round blocks) and use `set()` component's 
method to change the sensor value. We will create a new scratch extension that contain just one block named `position` 
and the user can change position's value by our python component.

## Extension class

`Extension` an *abstract* class is what you should implement if you want create your own extension. The only method that
you must implement to make it concrete is `do_init_components()` where you can create your own components and return as
list (or iterator in general). In this case you need just a component and you can use specialized `Sensor` component 
(reporters without arguments): 

    def do_init_components(self):
        self.component = Sensor.create(self, name="position")
        return [self.component]

Now we can change sensor's value simply by `ex.component.set(new_val)` or hide it by delegating set method in a more 
readable `change_position()` extension method:

    def change_position(self, position):
        self.component.set(position)

Your extension call doesn't need nothing else. You can 

 1. instantiate it `extension=MyFirstScratchExtension()`
 2. create service by `es=ExtensionService(extension)`
 3. save json extension descriptor by `save_service_description()` helper
 4. start service by `es.start()`
 
NOw you can import extension descriptor in Scratch:

Open Scratch, hold shift and click File menu: 

 - Chose *Import experimental HTTP Extension*
 - Browse to where you saved json extension descriptor and select it
 - Build: When "green flag" clicked, forever set x to position where position is a gray sensor in More Blocks
 
Now your sprite will be set in `x` position that you set by `change_position()` extension's method.


# Future directions
 
# Licence 
