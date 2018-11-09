Role description containing some reStructuredText expressions.

**Role variables**

.. zuul:rolevar:: mandatory_variable

   This variable is mandatory.


.. zuul:rolevar:: optional_variable
   :default: some_value

   This one is not.


.. zuul:rolevar:: list_variable
   :default: []
   :type: list

   This one must be a list.
