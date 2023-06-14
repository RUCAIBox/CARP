# -*- coding: utf-8 -*-
# :Copyright: © 2011 Günter Milde.

# ===================================================================
#       unimathsymbols.txt format description and parser
# ===================================================================
#
# The file ``unimathsymbols.txt`` contains a mapping between Unicode
# math characters and LaTeX math control sequences. Due to history and
# conceptual differences, this mapping is sometimes ambiguous and
# incomplete.
#
# This file explains the data format by example of a parser written as
# Python module. Load it the usual Python way
#
# >>> import parse_unimathsymbols
# >>> from parse_unimathsymbols import *
#
# .. contents::
#
# Requirements
# ------------
#
# Python Standard Library modules::
import os
import re, copy, unicodedata, configparser

# Configuration
# -------------
#
# datafilenames
# ~~~~~~~~~~~~~
# Paths to the data files::

pardir = os.path.abspath(os.path.join(__file__, os.pardir))
datafilename = 'processors/unimathsymbols.txt'
datafilename = os.path.join(pardir, datafilename)
mathtypes_filename = 'processors/category2mathtype.txt'
mathtypes_filename = os.path.join(pardir, mathtypes_filename)
packages_filename = 'processors/packages.txt'
packages_filename = os.path.join(pardir, packages_filename)

# delimiter
# ~~~~~~~~~
# Data fields are divided by a CIRCUMFLEX ACCENT::

delimiter = '^'

# comment_char
# ~~~~~~~~~~~~
# Lines starting with a NUMBER SIGN are ignored. Number signs at later
# positions do not start a comment. ::

comment_char = '#'


# superpackages
# ~~~~~~~~~~~~~
#
# Packages providing (almost) all symbols of another package.
# They are listed in the file ``packages.txt`` (cf. datafilenames_)
# in ConfigParser_ format::

superpackages = configparser.RawConfigParser()
superpackages.optionxform = str # case sensitive options
superpackages.read(packages_filename)

# *Sections* correspond to (sub) packages:
#
# >>> s = superpackages.sections()
# >>> s.sort()
# >>> s[:4]
# ['amsfonts', 'amsmath', 'amssymb', 'bbold']
#
# *Options* are packages providing the commands of the containing
# section:
#
# >>> superpackages.options('txfonts')
# ['kmath', 'kpfonts', 'pxfonts']
#
# *option values* are exceptions, i.e. commands not provided by
# the superpackage:
#
# >>> superpackages.items('txfonts')
# [('kmath', ''), ('kpfonts', '\\mathcent\n\\invamp; mirrored instead of turned'), ('pxfonts', '')]
#
# The `is_supported()`_ and `provided_by()`_ methods of an `UniMathEntry`_
# can be used to query the superpackage data.
#
# .. _ConfigParser: http://docs.python.org/library/configparser.html
#
# Data types
# ----------
#
# Classes for storing metadata for one character (UniMathEntry_) and a
# set of characters (Table_) and a function to generate a new
# UniMathEntry with default data (new_entry_).
#
# UniMathEntry
# ~~~~~~~~~~~~
#
# Data structure representing one character. Initialized with a string
# in the format of the `datafile`
#
# The function `read_data()`_ (below) creates `UniMathEntry` instances for
# the lines in the `datafile` (data fields separated by the delimiter_
# and optional whitespace):
#
# >>> data = read_data()
# >>> type(data[0x24])
# <class 'parse_unimathsymbols.UniMathEntry'>
#
# ::

class UniMathEntry(object):

    def __init__(self, line):
        """Parse one `line` of unimathsymbols.txt"""

        self.delimiter = delimiter
        fields = [i.strip() for i in line.split(delimiter)]

# data fields
# """""""""""
# ::

        (self.codepoint,     # Unicode Number
         self.utf8,          # literal character in UTF-8 encoding
         self.cmd,           # LaTeX command
         self.unicode_math,  # macro of the unicode-math package
         self.math_class,    # Unicode math character class
         self.category,      # math category of the symbol
         self.requirements,  # package(s) providing the command
         self.comment        # aliases and comments
        ) = fields

# Convert code point to integer (other values remain strings)::

        self.codepoint = int(self.codepoint, 16)

# Add missing literal characters (e.g. the delimiter)::

        if not self.utf8:
            self.utf8 = chr(self.codepoint).encode('utf8')
            # prepend base char to combining chars.
            if unicodedata.combining(chr(self.codepoint)):
                self.utf8 = 'x' + self.utf8
                # self.utf8 = u'\xA0'.encode('utf8') + self.utf8 # NBSP
            
# Example:
#
# >>> data[0x24].codepoint, data[0x24].utf8, data[0x24].cmd
# (36, '$', '\\$')
#
# Missing literal characters are regenerated:
#
# >>> data[ord(delimiter)].utf8
# '^'
#
# string representations
# """"""""""""""""""""""
#
# The string representation of a data entry is the data line
# (without the optional whitespace)::

    def __str__(self):
        # do not include the delimiter
        if self.utf8 == delimiter:
            self.utf8 = ''
        return self.delimiter.join(('%05X' % self.codepoint,
                                   self.utf8,
                                   self.cmd,
                                   self.unicode_math,
                                   self.math_class,
                                   self.category,
                                   self.requirements,
                                   self.comment
                                  ))
    
# We know the encoding is 'utf8', so unicode() should use it::

    def __unicode__(self):
        return str(self).decode('utf8')

# Examples:
#
# >>> str(data[0x24])
# '00024^$^\\$^\\mathdollar^N^mathord^^= \\mathdollar, DOLLAR SIGN'
# >>> print unicode(data[0xA5])
# 000A5^¥^\yen^\yen^N^mathord^amsfonts^YEN SIGN
# >>> print unicode(data[0x5e]) # leave out delimiter
# 0005E^^\sphat^^N^mathord^amsxtra^CIRCUMFLEX ACCENT, TeX superscript operator
#
# requirements
# """"""""""""
#
# Some symbols are provided by LaTeX packages which must be loaded to
# prevent an ``Undefined control sequence`` error.
#
# provided_by()
# '''''''''''''
#
# Recursively expand the package list in self.requirements with
# superpackages_::

    def provided_by(self, providers=[]):
        """Return sorted list of packages meeting providing the symbol via
        `self.cmd`.

        (The optional argument `providers` is used for recursion.)
        """
        if not providers:
            providers = [pkg for pkg in self.requirements.split()
                         if not pkg.startswith('-')]
        # Add "superpackages" providing the command:
        for pkg in providers[:]:
            if pkg not in superpackages.sections():
                continue
            for (superpkg, exceptions) in superpackages.items(pkg):
                # skip, if `self.cmd` contains a cmd from the exceptions
                # (check all cmds in a sequence, trim cmd arguments):
                if [1 for match in re.finditer(r'\\.[a-zA-Z]+', self.cmd)
                    if match.group(0) in exceptions]:
                    continue
                # append and recurse
                providers.append(superpkg)
                providers.extend(self.provided_by([superpkg]))
    # Return sorted list of unique entries:
        return Table([(pkg, True) for pkg in providers]).sortedkeys()


# Packages providing the ``\yen`` command:
#
# >>> print data[0xA5].provided_by()  # ¥
# ['MnSymbol', 'amsfonts', 'amssymb', 'oz']
#
# Recursion: `eufrac` is part of `amsfonts` is part of `amssymb` and related
#
# >>> print data[0x210C].requirements # ℌ
# eufrak
# >>> data[0x210C].provided_by()[:4]
# ['MnSymbol', 'amsfonts', 'amssymb', 'eufrak']
#
# conflicts_with()
# ''''''''''''''''
#
# A package name in the `requirements` field preceded by ``-`` indicates
# that the package redefines the command so it no longer produces the symbol.
# ::

    def conflicts_with(self, clashes=[]):
        """Return sorted list of packages redefining `self.cmd`.

        (The optional argument `clashes` is used for recursion.)
        """
        if not clashes:
            clashes = [pkg[1:] for pkg in self.requirements.split()
                         if pkg.startswith('-')]
        # Add "superpackages" providing the command:
        for pkg in clashes[:]:
            if pkg not in superpackages.sections():
                continue
            for (superpkg, exceptions) in superpackages.items(pkg):
                # skip, if `self.cmd` contains a cmd from the exceptions
                # (check all cmds in a sequence, trim cmd arguments):
                if [1 for match in re.finditer(r'\\.[a-zA-Z]+', self.cmd)
                    if match.group(0) in exceptions]:
                    continue
                # append and recurse
                clashes.append(superpkg)
                clashes.extend(self.provided_by([superpkg]))
    # Return sorted list of unique entries:
        return Table([(pkg, True) for pkg in clashes]).sortedkeys()


# `marvosym` redefines the standard LaTeX cmd ``\Rightarrow`` to a bold
# arrow:
#
# >>> data[0x21D2].requirements # ⇒
# '-marvosym'
# >>> data[0x21D2].conflicts_with()
# ['marvosym']
#
# is_supported()
# ''''''''''''''
#
# The `is_supported` method can be used to test whether a given set of
# LaTeX packages provides the symbol via ``self.cmd``.
# (The `supported_cmd()`_ method checks also alias commands.) ::

    def is_supported(self, packages):
        """Check if entry is supported by the list of `packages`.
        """
        if not self.cmd: # no LaTeX cmd
            return False
        providers = self.provided_by() or ['']
        clashes = self.conflicts_with()
        # iterate over reversed list -> last wins:
        for pkg in packages[::-1]: 
            if pkg in clashes:
                return False
            if pkg in providers:
                return True
        return False

# Examples:
#
# The yen sign is not supported by `lmodern` or `inputenc`
# but by `amssymb` and its superpackages_:
#
# >>> data[0xA5].is_supported(['lmodern', 'inputenc'])
# False
# >>> data[0xA5].is_supported(['lmodern', 'inputenc', 'amssymb'])
# True
# >>> data[0xA5].is_supported(['MnSymbol']) # superpackage of amssymb
# True
#
# Standard commands are only listed as supported, if the empty string is
# part of the package list:
#
# >>> data[0x20D7].is_supported(['amssymb']) # \vec
# False
# >>> data[0x20D7].is_supported(['', 'amssymb']) # \vec
# True
#
# However, if the empty string is followed by a conflicting package,
# the entry is not supported.
#
# >>> data[0x20D7].is_supported(['', 'wrisym'])
# False
#
# Like in a LaTeX document, the last package (re)defining the command "wins":
# >>> data[0x20D7].is_supported(['wrisym', ''])
# True
#
# name clash between two packages:
#
# >>> print unicode(data[0x03DC])
# 003DC^Ϝ^\Digamma^\upDigamma^A^mathalpha^wrisym -amssymb^= \digamma (amssymb), capital digamma
# >>> print unicode(data[0x03DD])
# 003DD^ϝ^\digamma^\updigamma^A^mathalpha^arevmath wrisym^GREEK SMALL LETTER DIGAMMA
#
# >>> data[0x03DC].is_supported(['wrisym'])
# True
# >>> data[0x03DC].is_supported(['amssymb'])
# False
# >>> data[0x03DC].is_supported(['amssymb', 'wrisym'])
# True
# >>> data[0x03DC].is_supported(['wrisym', 'amssymb'])
# False
# >>> data[0x03DD].is_supported(['wrisym'])
# True
#
#
# related_commands
# """"""""""""""""
#
# Related commands are listed in the "comment" field. They are marked by a
# character denoting its type and separated by commas.
# The `type` characters match the ones used in Unicode's NamesList.txt
# (cf. http://www.unicode.org/Public/UNIDATA/NamesList.html):
#
# :=:  equals  (alias commands),
# :#:  approx  (similar, symbol variants and replacements),
# :x:  not     (false friends).
#
# Requirements of related commands are given in parentheses, e. g.,
# ``\widehat (amssymb)``.
#
# Examples:
#
# >>> data[0x24].comment
# '= \\mathdollar, DOLLAR SIGN'
# >>> data[0x2F].comment
# '# \\slash, SOLIDUS'
# >>> data[0x03F4].comment
# 'x \\varTheta (amssymb), GREEK CAPITAL THETA SYMBOL'
#
# cmd_comment()
# '''''''''''''
#
# Generate a string suitable to place the original command and
# requirements in the comment field of a new entry for related commands.
# Used by `sort_by_command()`_. ::

    def cmd_comment(self):
        """Return "<self.cmd> (<self.requirements>)"

        (or just self.cmd if there are no requirements).
        """
        cc = self.cmd
        if self.requirements :
            cc += ' (%s)' % self.requirements
        return cc

# Examples:
#
# >>> data[0x24].cmd_comment()
# '\\$'
# >>> data[0xA5].cmd_comment()
# '\\yen (amsfonts)'
#
# parse_cmd_comment()
# '''''''''''''''''''
#
# Return (type, cmd, requirements) tuple for command-comment `cc`.
#
# This auxiliary function is used by `related_commands()`_. Its a class
# method because it belongs here although it does not use the `self`
# argument. ::

    def parse_cmd_comment(self, cc):
        # cc has the form '<type> <cmd> (<requirements>)'
        # requirements are also space delimited: get content of ( ):
        requirements = re.search('\(([^\)]+)\)', cc)
        if requirements is None:
            requirements = ''
        else:
            requirements = requirements.group(1)
        return cc.split()[0], requirements

# Examples:
#
# >>> data[0x03F4].parse_cmd_comment(r' \$')
# ('\\$', '')
# >>> data[0x03F4].parse_cmd_comment(r'\yen (amsfonts)')
# ('\\yen', 'amsfonts')
#
#
# related_commands()
# ''''''''''''''''''
#
# The `related_commands` method returns a list of UniMathEntry instances
# for the related commands of the type indicated by `typechar`.
# The "used" command-comment is removed from the comment field. ::

    def related_commands(self, typechar):
        """Return list of entries for related commands.
        """
        entries = []
        cmtlist = self.comment.split(',')
        for i, part in enumerate(cmtlist):
            part = part.strip()
            if part.startswith(typechar):
                new = copy.copy(self)
                new.cmd, new.requirements = self.parse_cmd_comment(part[1:])
                # leave out the comment part for this cmd
                new.comment = ', '.join(cmtlist[:i] + cmtlist[i+1:])
                entries.append(new)
        return entries

# Examples:
#
# There is no alias for the YEN SIGN, one alias for the DOLLAR SIGN
# and one substitute for the MIDDLE DOT:
#
# >>> data[0xA5].related_commands('=')
# []
#
# >>> print data[0x24].related_commands('=')[0]
# 00024^$^\mathdollar^\mathdollar^N^mathord^^ DOLLAR SIGN
#
# >>> print unicode(data[0xB5].related_commands('#')[0]) # MICRO SIGN
# 000B5^µ^\mathrm{\mu}^^N^mathalpha^omlmathrm^= \tcmu (mathcomp),  t \textmu (textcomp),  # \muup (kpfonts mathdesign),  MICRO SIGN
#
# supported_cmd()
# '''''''''''''''
# This method is used by the scripts producing LaTeX documents to
# get a command that works with a given set of extension packages::

    def supported_cmd(self, packages):
        """Return cmd or alias command if it is supported by `packages`.
        """
        if self.is_supported(packages):
            return self.cmd
        for alias in self.related_commands('='):
            if alias.is_supported(packages):
                return alias.cmd
        return ''

# The capital Digamma is provided under different names:
#
# >>> print data[0x03DC].supported_cmd(['amssymb'])
# \digamma
# >>> print data[0x03DC].supported_cmd(['wrisym'])
# \Digamma
#
# substitution_cmd()
# ''''''''''''''''''
# This method is used by the scripts producing LaTeX documents to
# get a command that works with a given set of extension packages::

    def substitution_cmd(self, packages):
        """Return substitution command
        if it is supported by `packages`.
        """
        for substitute in self.related_commands('#'):
            if substitute.is_supported(packages):
                return '%s' % substitute.cmd
        return ''



# Examples:
#
# The MICRO SIGN is provided by `mathcomp`. An upright \mu can be used
# as substitution.:
#
# >>> data[0xB5].supported_cmd(['mathcomp'])
# '\\tcmu'
# >>> print data[0xB5].substitution_cmd(['omlmathrm'])
# \mathrm{\mu}
# >>> print data[0xB5].substitution_cmd(['kpfonts'])
# \muup
#
# new_entry
# ---------
#
# The function `new_entry` returns an UniMathEntry instance for the
# given code point with default data for `number`, `utf8`, `mathtype`
# (converted from unicodedata.category), and `comment` (Unicode name).
#
# >>> print unicode(new_entry(0x00AE))
# 000AE^®^^^^mathord^^REGISTERED SIGN
#
# >>> unicodedata.category(chr(0x02c6))
# 'Lm'
# >>> print unicode(new_entry(0x02C6))
# 002C6^ˆ^^^^mathalpha^^MODIFIER LETTER CIRCUMFLEX ACCENT
#
# ::

def new_entry(number, delimiter=delimiter):
    """Return a new UniMathEntry for Unicode char with `number`

    Raise ValueError, is there is no Unicode character with that number.
    """
    # Mapping from Unicode category to LaTeX math category:
    mathtypes = configparser.SafeConfigParser()
    mathtypes.read(mathtypes_filename)

    uc = chr(number)
    utf8 = uc.encode('utf-8')
    try:
        mathtype = mathtypes.get('mathtypes', unicodedata.category(uc))
    except configparser.NoOptionError:
        mathtype = ''
    # special cases:
    if utf8 == delimiter:
        utf8 = ' '
    if unicodedata.combining(uc):
        utf8 = 'x' + utf8
        # mathtype = 'mathaccent'
    line = delimiter.join(('%05X' % number,
                           # do not print the literal char if it is the delimiter:
                           utf8,
                           '', # command,
                           '', # unicode-math,
                           '', # math character class
                           mathtype,
                           '', # requirements,
                           unicodedata.name(uc) # comment
                          ))
    return UniMathEntry(line)

# Table
# ~~~~~
#
# As the math characters are a subset of Unicode with "gaps" between the
# character numbers, the Python representation uses a dictionary with
# additional sorting methods (while, e.g., Lua could use the standard
# `Table` data type)::

# >>> ts = Table({'zero': 0, 'one': 1})
# >>> tn = Table({0: 'zero', 1: 'one'})
#
# To get a list of sorted keys, do
#
# >>> print ts.sortedkeys(), tn.sortedkeys()
# ['one', 'zero'] [0, 1]
#
# Iterating over the Table is done using the sorted keys:
#
# >>> print [(key, value) for key, value in ts]
# [('one', 1), ('zero', 0)]
#
# Test for existence of a key like a standard dict:
# >>> 'zero' in ts
# True
# >>> 'zero' in tn
# False
#
# ::

class Table(dict):

    def sortedkeys(self):
        """Return sorted list of keys"""
        keys = list(self.keys())
        keys.sort()
        return keys

    def __iter__(self):
        """Return iterator over sorted (key, value) pairs"""
        for key in self.sortedkeys():
            yield key, self[key]

# The `add_unique` function is used to avoid overwriting existing values:
#
# >>> ts.add_unique('one', 1.)
#
# >>> print [(key, value) for key, value in ts]
# [('one', 1), ('one~', 1.0), ('zero', 0)]
#
# ::

    def add_unique(self, key, value):
        """Add `value`. Make `key` unique.

        Expects a string key. Appends "~" until the key is unique
        ('~' sorts after letters).
        """
        while key in self:
            key += '~'
        self[key] = value




# Read/Write data file
# --------------------
#
# Functions for reading and writing the data file.
#
#
# read_data()
# ~~~~~~~~~~~
# ::

def read_data(path=datafilename):
    """Return Table of data entries in the data file.
    """
    datafile = open(path, 'r', encoding="utf-8")
    data = Table()

# Read lines and add UniMathEntry instances to the `data` table. Skip
# comments and empty lines. Use the Unicode character number as key::

    for line in datafile:
        if line.startswith(comment_char) or not line.strip():
            continue
        try:
            entry = UniMathEntry(line)
        except:
            print("error in line", line)
            raise
        data[entry.codepoint] = entry

# Close and return::

    datafile.close()
    return data


# read_header()
# ~~~~~~~~~~~~~
# ::

def read_header(path=datafilename):
    """Return leading comment block of the data file as list of lines.
    """
    datafile = open(path, 'r')
    header = []

    for line in datafile:
        if not line.startswith(comment_char):
            break
        header.append(line)

    datafile.close()
    return header


# write_data()
# ~~~~~~~~~~~~
#
# Write a Table_ instance with UniMathEntry_ data records (like the one
# returned by `read_data()`_) to the file-like object `outfile`::

def write_data(data, outfile):
    """Write `data` to `outfile`"""

    try:
        outfile.write(''.join(data.header))
    except AttributeError:
        print("no data.header")
    for (key, value) in data:
        outfile.write(str(value) + '\n')


# Data processing
# ---------------
#
# Functions to sort and filter.
#
# sort_by_command()
# ~~~~~~~~~~~~~~~~~
#
# Return a Table with LaTeX command as key. For each Unicode char,
# insert records for command and aliases.
#
# >>> cmds = sort_by_command(data)
# >>> print unicode(cmds[r'\ast'])
# 02217^∗^\ast^\ast^B^mathbin^^ASTERISK OPERATOR (Hodge star operator)
#
# Aliases get separate entries:
#
# >>> print unicode(cmds[r'\neg'])
# 000AC^¬^\neg^\neg^U^mathord^^= \lnot, NOT SIGN
#
# >>> print unicode(cmds[r'\lnot'])
# 000AC^¬^\lnot^\neg^U^mathord^^= \neg,  NOT SIGN
#
# ::

def sort_by_command(data):
    """Return `data` as a Table with LaTeX command as key.
    """
    commands = Table()

    for (key, entry) in data:
        if  entry.cmd: # and entry.cmd != entry.utf8:
            commands.add_unique(entry.cmd, entry)
        for alias in entry.related_commands('='):
            alias.comment = '= %s, %s' % (entry.cmd_comment(),
                                          alias.comment)
            commands.add_unique(alias.cmd, alias)
    return commands


# substitution_commands()
# ~~~~~~~~~~~~~~~~~~~~~~~
#
# Return a Table with LaTeX substitution commands as key. 
# For each Unicode char insert records for approximate matches.
#
# >>> ersatzcmds = substitution_commands(data)
# >>> print unicode(data[0x210F])
# 0210F^ℏ^\hslash^\hslash^N^mathalpha^amssymb fourier arevmath^=\HBar (wrisym), #\hbar, Planck's h over 2pi
# >>> print unicode(ersatzcmds[r'\hbar'])
# 0210F^ℏ^\hbar^\hslash^N^mathalpha^^= \hslash (amssymb fourier arevmath), =\HBar (wrisym),  Planck's h over 2pi
#
# ::

def substitution_commands(data):
    """Return LaTeX substitutuion commands (with cmd as key).
    """
    ersatzcommands = Table()

    for (key, entry) in data:
        for ersatz in entry.related_commands('#'):
            if entry.cmd:
                ersatz.comment = '= %s, %s' % (entry.cmd_comment(),
                                               ersatz.comment)
            ersatzcommands.add_unique(ersatz.cmd, ersatz)
    return ersatzcommands



# Default action
# --------------
# ::

if __name__ == '__main1__':
    import sys, difflib

    header = read_header()
    data = read_data()

# Add a new entries::

    def add_entry(cp, cmd='', requirements=''):
        data[cp] = new_entry(cp)
        data[cp].cmd = cmd
        data[cp].requirements = requirements

    # data.add_entry(0x2620, r'\skull', 'arevmath')

# Process data::

#     for key, entry in data:
        # if entry.requirements != 'omlmathit':
        # if not entry.cmd.startswith(r'\mathit'):
        # if not re.match(r'\\[A-Z]', entry.cmd):
        # if not entry.cmd.startswith(r'\mathbfit'):
        # if not (re.search(r'\\mathrm\{\\[A-Z]', entry.comment)):
            # continue
        # print entry
        # if not entry.comment.startswith(r'= \mathbold'):
        #     cc = '= ' + entry.cmd_comment()
        #     cc = cc.replace('mathbfit', 'mathbold')
        #     cc = cc.replace('isomath', 'fixmath')
        #     entry.comment = cc + ', ' + entry.comment

        # entry.comment = re.sub(r'(\\mathit\{\\[A-Z][a-z]+\})', r'\1 (-fourier)',
        #                        entry.comment)

        # cc = '= ' + entry.cmd_comment()
        # entry.comment = cc + ', ' + entry.comment
        # entry.cmd = cmd
        # entry.requirements += '-fourier'

        # # normalize white-space in comments
        # entry.comment = ' '.join(entry.comment.split())

    # Write to outfile?:
    outfile = None
    # outfile = file('../data/unimathsymbols.txt', 'w')
    # outfile = sys.stdout


# Test for differences after a read-write cycle. Whitespace adjacent to the
# delimiter is not significant. ::

    in_lines = open(datafilename, 'r').readlines()
    in_lines = [# '^'.join([field.strip(' \t') for field in line.split('^')])
                re.sub(r'[ \t]*\^[ \t]*', '^', line).rstrip() + '\n'
                for line in in_lines]

    header = [re.sub(r' *\^ *', '^', line) for line in header]

    out_lines = [str(v)+'\n' for (k,v) in data]

    diff = ''.join(difflib.unified_diff(in_lines, header + out_lines,
                                        datafilename, '*round trip*'))
    if diff:
        print(diff)
    else:
        print('no differences after round trip')

# Write back to outfile::

    if outfile:
        data.header = header
        write_data(data, outfile)
        if outfile != sys.stdout:
            print("Output written to", outfile.name)

    # for (key, entry) in sort_by_command(data):
    #     print entry

# New entries
#
# ::

    # for i in range(0x2336, 0x237A):
    #     print new_entry(i)

    print('%d characters' % len(data))
