import glob
import sys
from xmltypes import ApiRegistry, Api

COPYRIGHT_HEADER = '''
   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2013 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
'''

def write_header(out):
    out.write('/* This file is autogenerated: do not edit */\n')
    out.write('/*%s*/\n' % COPYRIGHT_HEADER)
    out.write('\n')

def write_footer(out):
    out.write('''
/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
''')

class SourceWriter:
    def __init__(self, out):
        self.out = out
        self._indent = 0

    def indent(self):
        self._indent += 1

    def outdent(self):
        self._indent -= 1

    def writeln(self, line=None):
        if line:
            self.out.write('%s%s\n' % ('  ' * self._indent, line))
        else:
            self.out.write('\n')

    def write_doc_comment(self, doc):
        self.write_comment(doc.as_text())

    def write_comment(self, doc):
        self.writeln('/*')
        self.indent()
        for line in doc.splitlines():
            self.writeln(line)
        self.outdent()
        self.writeln('*/')

    def write_begin_extern_c(self):
        self.writeln('#ifdef __cplusplus')
        self.writeln('extern "C" {')
        self.writeln('#endif')

    def write_end_extern_c(self):
        self.writeln('#ifdef __cplusplus')
        self.writeln('}')
        self.writeln('#endif')

def write_api(api, out):
    writer = SourceWriter(out)
    write_header(out)

    if api.get_xml_name() == 'rtl':
        out.write('''
/* FIXME: rationalize these headers */
#include "gcc-common.h"
#include "tree-flow.h"
#include "rtl.h"
''')
    else:
        out.write('#include "gcc-common.h"\n')
    writer.writeln()

    writer.write_begin_extern_c()

    doc = api.get_doc()
    if doc:
        writer.write_doc_comment(doc)
        writer.writeln()

    for type_ in api.iter_types():
        writer.writeln('/* %s */\n' % type_.get_c_name())

        doc = type_.get_doc()
        if doc:
            writer.write_doc_comment(doc)

        # mark_in_use:
        writer.writeln('GCC_PUBLIC_API(void)')
        writer.writeln('%s_mark_in_use(%s %s);'
                       % (type_.get_c_prefix(),
                          type_.get_c_name(),
                          type_.get_varname()))
        writer.writeln()

        # add getters for attributes:
        for attr in type_.iter_attrs():
            doc = attr.get_doc()
            if doc:
                writer.write_doc_comment(doc)
            if attr.get_c_name().startswith('is_'):
                # "gcc_foo_is_some_boolean", rather than
                # "gcc_foo_get_is_some_boolean":
                writer.writeln('GCC_PUBLIC_API(%s)' % attr.get_c_type())
                writer.writeln('%s_%s(%s %s);'
                               % (type_.get_c_prefix(),
                                  attr.get_c_name(),
                                  type_.get_c_name(),
                                  type_.get_varname()))
            else:
                writer.writeln('GCC_PUBLIC_API(%s)' % attr.get_c_type())
                writer.writeln('%s_get_%s(%s %s);'
                               % (type_.get_c_prefix(),
                                  attr.get_c_name(),
                                  type_.get_c_name(),
                                  type_.get_varname()))
            writer.writeln()

        # add iterators
        for iter_ in type_.iter_iters():
            itertype = iter_.get_type()
            writer.write_comment('Iterator; terminates if the callback returns truth\n'
                                 '(for linear search)')
            writer.writeln('GCC_PUBLIC_API(bool)')
            writer.writeln('%s_for_each_%s(%s %s,'
                           % (type_.get_c_prefix(),
                              iter_.get_c_name(),
                              type_.get_c_name(),
                              type_.get_varname()))
            writer.writeln('    bool (*cb)(%s %s, void *user_data),'
                           % (itertype.get_c_name(),
                              itertype.get_varname()))
            writer.writeln('    void *user_data);')
            writer.writeln()

        # add upcasts
        for base in type_.get_bases():
            writer.writeln('GCC_PUBLIC_API(%s)'
                           % base.get_c_name())
            writer.writeln('%s_as_%s(%s %s);'
                           % (type_.get_c_prefix(),
                              base.get_c_name(),
                              type_.get_c_name(),
                              type_.get_varname()))
            writer.writeln()

        # add downcasts
        for subclass in type_.get_subclasses(recursive=True):
            writer.writeln('GCC_PUBLIC_API(%s)'
                           % subclass.get_c_name())
            writer.writeln('%s_as_%s(%s %s);'
                           % (type_.get_c_prefix(),
                              subclass.get_c_name(),
                              type_.get_c_name(),
                              type_.get_varname()))
            writer.writeln()

    # add getters for attributes:
    for attr in api.iter_attrs():
        doc = attr.get_doc()
        if doc:
            writer.write_doc_comment(doc, out)
        if attr.is_readable():
            writer.writeln('GCC_PUBLIC_API(%s)' % attr.get_c_type())
            writer.writeln('gcc_get_%s(void);' % attr.get_c_name())
        if attr.is_writable():
            writer.writeln('GCC_PUBLIC_API(void)')
            writer.writeln('gcc_set_%s(%s %s);'
                           % (attr.get_c_name(),
                              attr.get_c_type(),
                              attr.get_varname()))
        writer.writeln()

    # add iterators
    for iter_ in api.iter_iters():
        itertype = iter_.get_type()
        writer.write_comment('  Iterator; terminates if the callback returns truth\n'
                             '  (for linear search).')
        writer.writeln('GCC_PUBLIC_API(bool)')
        writer.writeln('gcc_for_each_%s(bool (*cb)(%s %s, void *user_data),'
                  % (iter_.get_c_name(),
                     itertype.get_c_name(),
                     itertype.get_varname()))
        writer.writeln('    void *user_data);')
        writer.writeln()

    writer.write_end_extern_c()
    write_footer(out)

def write_public_types(registry, out):
    writer = SourceWriter(out)
    write_header(out)
    out.write('#ifndef INCLUDED__GCC_PUBLIC_TYPES_H\n')
    out.write('#define INCLUDED__GCC_PUBLIC_TYPES_H\n')
    out.write('\n')
    out.write('#include "gcc-semiprivate-types.h"\n')
    out.write('\n')
    writer.write_begin_extern_c()
    for api in registry.apis:
        out.write('/* Opaque types: %s */\n' % api.get_doc().as_text())
        for type_ in api.iter_types():
            out.write('typedef struct %s %s;\n'
                      % (type_.get_c_name(), type_.get_c_name()))
        out.write('\n')

    writer.write_end_extern_c()
    out.write('#endif /* INCLUDED__GCC_PUBLIC_TYPES_H */\n')
    write_footer(out)

def write_semiprivate_types(registry, out):
    writer = SourceWriter(out)
    write_header(out)
    out.write('#ifndef INCLUDED__GCC_SEMIPRIVATE_TYPES_H\n')
    out.write('#define INCLUDED__GCC_SEMIPRIVATE_TYPES_H\n')

    out.write('\n')
    out.write('#include "input.h" /* for location_t */\n')
    out.write('#include "options.h" /* for enum opt_code */\n')
    out.write('\n')
    writer.write_begin_extern_c()
    out.write('/*\n')
    out.write('  These "interface types" should be treated like pointers, only that\n')
    out.write('  users are required to collaborate with the garbage-collector.\n')
    out.write('\n')
    out.write('  The internal details are exposed here so that the debugger is able to\n')
    out.write('  identify the real types.  Plugin developers should *not* rely on the\n')
    out.write('  internal implementation details.\n')
    out.write('\n')
    out.write('  By being structs, the compiler will be able to complain if plugin code\n')
    out.write('  directly pokes at a pointer.\n')
    out.write('*/\n')

    for api in registry.apis:
        out.write('/* Semiprivate types: %s */\n' % api.get_doc().as_text())
        for type_ in api.iter_types():
            out.write('struct %s {\n' % type_.get_c_name())
            out.write('  %s inner;\n' % type_.get_inner_type())
            out.write('};\n')
            out.write('\n')
            out.write('GCC_PRIVATE_API(struct %s)\n' % type_.get_c_name())
            out.write('gcc_private_make_%s(%s inner);\n'
                      % (type_.get_xml_name(),
                         type_.get_inner_type()))
            out.write('\n')

    writer.write_end_extern_c()
    out.write('#endif /* INCLUDED__GCC_SEMIPRIVATE_TYPES_H */\n')
    write_footer(out)

registry = ApiRegistry()
for xmlfile in sorted(glob.glob('*.xml')):
    api = Api(registry, xmlfile)
for api in registry.apis:
    with open(api.get_header_filename(), 'w') as f:
        # write(api, sys.stdout)
        write_api(api, f)
    with open('gcc-public-types.h', 'w') as f:
        write_public_types(registry, f)
    with open('gcc-semiprivate-types.h', 'w') as f:
        write_semiprivate_types(registry, f)
