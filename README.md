# motley

> Rocking terminal colours. Just like in the 80s. 🏳️‍🌈🤘🏽🎸

<!--
TODO
[![Build Status](https://travis-ci.com/astromancer/motley.svg?branch=master)](https://travis-ci.com/astromancer/motley)
[![Documentation Status](https://readthedocs.org/projects/motley/badge/?version=latest)](https://motley.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/motley.svg)](https://pypi.org/project/motley)
[![GitHub](https://img.shields.io/github/license/astromancer/motley.svg?color=blue)](https://motley.readthedocs.io/en/latest/license.html)
 -->

A python library for playing with colourful string representations using ANSI escape sequences.



# Install

```shell
pip install https://github.com/astromancer/motley
```

# Use

<!-- ## Examples -->

## Colouring and Styling Text

### Stylization via extended format directives
 
```python
>>> motley.format('This text is {:|g}!'.format('green')
```

```python
>>> motley.format('{:{:|g} {:|bB_}!<13}'.format('Hello', 'World')
```

### Convenience functions
```python
>>> motley.green_on_white(':)')
```

<!-- ![Example Image](https://github.com/astromancer/motley/blob/master/tests/images/example_0.png "Example Image") -->


<!-- For more examples see [Documentation]() -->

<!-- # Documentation
TODO -->

# Test

The [`test suite`](./tests) contains further examples of how
`motley` can be used.  Testing is done with `pytest`:

```shell
pytest motley
```

# Contribute
Contributions are welcome!

1. [Fork it!](https://github.com/astromancer/motley/fork)
2. Create your feature branch\
    ``git checkout -b feature/rad``
3. Commit your changes\
    ``git commit -am 'Add some cool feature 😎'``
4. Push to the branch\
    ``git push origin feature/rad``
5. Create a new Pull Request

# Contact

* e-mail: hannes@saao.ac.za

<!-- ### Third party libraries
 * see [LIBRARIES](https://github.com/username/sw-name/blob/master/LIBRARIES.md) files -->

# License

* see [LICENSE](https://github.com/astromancer/motley/blob/master/LICENSE)


<!-- # Version
This project uses a [semantic versioning](https://semver.org/) scheme. The 
latest version is
* {version} -->

