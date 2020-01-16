from docutils import nodes
from sphinx.locale import _
from docutils.nodes import Element, Admonition
from sphinx.util.docutils import SphinxDirective
from docutils.parsers.rst.roles import set_classes
from docutils.parsers.rst.directives.admonitions import BaseAdmonition


class example(nodes.Admonition, nodes.Element):
    pass


class ExampleDirective(BaseAdmonition):
    node_class = example
    optional_arguments = 1

    def run(self):
        set_classes(self.options)
        self.assert_has_content()
        text = '\n'.join(self.content)
        admonition_node = self.node_class(text, **self.options)
        self.add_name(admonition_node)
        if self.arguments:
            title_text = 'Example: ' + self.arguments[0]
        else:
            title_text = 'Example'

        textnodes, messages = self.state.inline_text(title_text,
                                                        self.lineno)
        title = nodes.title(title_text, '', *textnodes)
        title.source, title.line = (
                self.state_machine.get_source_and_line(self.lineno))
        admonition_node += title
        admonition_node += messages

        self.state.nested_parse(self.content, self.content_offset,
                                admonition_node)
        return [admonition_node]



def visit_example_node(self, node):
    self.body.append(self.starttag(
        node, 'div', CLASS=('admonition example-directive')))
    self.set_first_last(node)


def depart_example_node(self, node):
    self.depart_admonition(node)


def setup(app):
    app.add_node(
        example,
        html=(visit_example_node, depart_example_node),
        latex=(visit_example_node, depart_example_node),
        text=(visit_example_node, depart_example_node)
    )
    app.add_directive('example', ExampleDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
