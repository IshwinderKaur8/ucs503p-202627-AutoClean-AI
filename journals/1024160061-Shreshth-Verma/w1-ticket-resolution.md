# Week 1 : Order of Flags in Compilation Command

# Order of Flags

## Error:

Error encountered during compilation.

> run_main.cpp:(.text.startup.main+0x68): undefined
> reference to `Bvr::Math::sum(int, int)'

## Relevant Context

In my `Makefile`, I define the recipe for binary file
as,

``` makefile
dist/bin/run : src/bin/run_main.cpp 
	$(CXX) $(CXXFLAGS) $(CFLAGS) $(LDFLAGS) $(FLAGS) \
	       -lbvr_math -o $@ $^
```

which during `make` translates to,

``` shell
c++ -O2 -Wall -Wextra -fPIC -std=c++17 -Iinc \
    [...]                                    \
    -Ldist/lib -lbvr_math -o dist/bin/run    \
    src/bin/run_main.cpp
```

## Key Observation

In this case the most likely error is in the order that
`-lbvr_math` precedes `src/bin/run_main.cpp`.  Whereas,
`-lbvr_math`, should follow `src/bin/run_main.cpp`.

## Solution
In the `Makefile`, the recipe should instead be defined as:

``` makefile
dist/bin/run : src/bin/run_main.cpp 
	$(CXX) $(CXXFLAGS) $(CFLAGS) $(LDFLAGS) $(FLAGS) \
	       -o $@ $^ -lbvr_math
```

**Because**

The generic definition of a recipe in `Makefile` is:

``` makefile
output_filename : dependency1 dependency2 [...]
	shell_command -o $@ $^
```

_Assuming that the_ `shell_command` *accepts a flag*
`-o` *for output filename and a list of input*
*filenames to process.*

