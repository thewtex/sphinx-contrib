# -*- coding: utf-8 -*-
"""
    packetdiag.sphinx_ext
    ~~~~~~~~~~~~~~~~~~~~~~

    Allow packetdiag-formatted diagrams to be included in Sphinx-generated
    documents inline.

    :copyright: Copyright 2010 by Takeshi Komiya.
    :license: BSDL.
"""

import posixpath
import os
import codecs
import traceback
try:
    from hashlib import sha1 as sha
except ImportError:
    from sha import sha

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx.errors import SphinxError
from sphinx.util.osutil import ensuredir, ENOENT, EPIPE
from sphinx.util.compat import Directive

from packetdiag_sphinxhelper import command, parser, builder, drawer
from packetdiag_sphinxhelper import collections, FontMap
from packetdiag_sphinxhelper import packetdiag, PacketdiagDirective
namedtuple = collections.namedtuple


class PacketdiagError(SphinxError):
    category = 'Packetdiag error'


class Packetdiag(PacketdiagDirective):
    def run(self):
        try:
            return super(Packetdiag, self).run()
        except parser.ParseException, e:
            if self.content:
                msg = '[%s] ParseError: %s\n%s' % (self.name, e, "\n".join(self.content))
            else:
                msg = '[%s] ParseError: %s\n%r' % (self.name, e, self.arguments[0])

            reporter = self.state.document.reporter
            return [reporter.warning(msg, line=self.lineno)]

    def node2image(self, node, diagram):
        return node


def get_image_filename(self, code, format, options, prefix='packetdiag'):
    """
    Get path of output file.
    """
    if format.upper() not in ('PNG', 'PDF', 'SVG'):
        raise PacketdiagError('packetdiag error:\nunknown format: %s\n' % format)

    if format.upper() == 'PDF':
        try:
            import reportlab
        except ImportError:
            msg = 'packetdiag error:\n' + \
                  'colud not output PDF format; Install reportlab\n'
            raise PacketdiagError(msg)

    hashkey = code.encode('utf-8') + str(options)
    fname = '%s-%s.%s' % (prefix, sha(hashkey).hexdigest(), format.lower())
    if hasattr(self.builder, 'imgpath'):
        # HTML
        relfn = posixpath.join(self.builder.imgpath, fname)
        outfn = os.path.join(self.builder.outdir, '_images', fname)
    else:
        # LaTeX
        relfn = fname
        outfn = os.path.join(self.builder.outdir, fname)

    if os.path.isfile(outfn):
        return relfn, outfn

    ensuredir(os.path.dirname(outfn))

    return relfn, outfn


def get_fontmap(self):
    try:
        fontmappath = self.builder.config.packetdiag_fontmap
        fontmap = FontMap(fontmappath)
    except:
        attrname = '_packetdiag_fontmap_warned'
        if not hasattr(self.builder, attrname):
            msg = ('packetdiag cannot load "%s" as fontmap file, '
                   'check the packetdiag_fontmap setting' % fontmappath)
            self.builder.warn(msg)
            setattr(self.builder, attrname, True)

        fontmap = FontMap(None)

    try:
        fontpath = self.builder.config.packetdiag_fontpath
        if isinstance(fontpath, (str, unicode)):
            fontpath = [fontpath]

        if fontpath:
            config = namedtuple('Config', 'font')(fontpath)
            _fontpath = command.detectfont(config)
            fontmap.set_default_font(_fontpath)
    except:
        attrname = '_packetdiag_fontpath_warned'
        if not hasattr(self.builder, attrname):
            msg = ('packetdiag cannot load "%s" as truetype font, '
                   'check the packetdiag_fontpath setting' % fontpath)
            self.builder.warn(msg)
            setattr(self.builder, attrname, True)

    return fontmap


def create_packetdiag(self, code, format, filename, options, prefix='packetdiag'):
    """
    Render packetdiag code into a PNG output file.
    """
    draw = None
    fontmap = get_fontmap(self)
    try:
        tree = parser.parse_string(code)
        screen = builder.ScreenNodeBuilder.build(tree)

        antialias = self.builder.config.packetdiag_antialias
        draw = drawer.DiagramDraw(format, screen, filename,
                                  fontmap=fontmap, antialias=antialias)
    except Exception, e:
        if self.builder.config.packetdiag_debug:
            traceback.print_exc()

        raise PacketdiagError('packetdiag error:\n%s\n' % e)

    return draw


def make_svgtag(self, image, relfn, trelfn, outfn,
                alt, thumb_size, image_size):
    svgtag_format = """<svg xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    alt="%s" width="%s" height="%s">%s
    </svg>"""

    code = open(outfn, 'r').read().decode('utf-8')

    return (svgtag_format %
            (alt, image_size[0], image_size[1], code))


def make_imgtag(self, image, relfn, trelfn, outfn,
                alt, thumb_size, image_size):
    result = ""
    imgtag_format = '<img src="%s" alt="%s" width="%s" height="%s" />\n'

    if trelfn:
        result += ('<a href="%s">' % relfn)
        result += (imgtag_format %
                   (trelfn, alt, thumb_size[0], thumb_size[1]))
        result += ('</a>')
    else:
        result += (imgtag_format %
                   (relfn, alt, image_size[0], image_size[1]))

    return result


def render_dot_html(self, node, code, options, prefix='packetdiag',
                    imgcls=None, alt=None):
    trelfn = None
    thumb_size = None
    try:
        format = self.builder.config.packetdiag_html_image_format
        relfn, outfn = get_image_filename(self, code, format, options, prefix)

        image = create_packetdiag(self, code, format, outfn, options, prefix)
        if not os.path.isfile(outfn):
            image.draw()
            image.save()

        # generate thumbnails
        image_size = image.pagesize()
        if 'maxwidth' in options and options['maxwidth'] < image_size[0]:
            thumb_prefix = prefix + '_thumb'
            trelfn, toutfn = get_image_filename(self, code, format,
                                                options, thumb_prefix)

            ratio = float(options['maxwidth']) / image_size[0]
            thumb_size = (options['maxwidth'], image_size[1] * ratio)
            if not os.path.isfile(toutfn):
                image.filename = toutfn
                image.save(thumb_size)

    except UnicodeEncodeError, e:
        msg = ("packetdiag error: UnicodeEncodeError caught "
               "(check your font settings)")
        self.builder.warn(msg)
        raise nodes.SkipNode
    except PacketdiagError, exc:
        self.builder.warn('dot code %r: ' % code + str(exc))
        raise nodes.SkipNode

    self.body.append(self.starttag(node, 'p', CLASS='packetdiag'))
    if relfn is None:
        self.body.append(self.encode(code))
    else:
        if alt is None:
            alt = node.get('alt', self.encode(code).strip())

        if format.upper() == 'SVG':
            tagfunc = make_svgtag
        else:
            tagfunc = make_imgtag

        self.body.append(tagfunc(self, image, relfn, trelfn, outfn, alt,
                                 thumb_size, image_size))

    self.body.append('</p>\n')
    raise nodes.SkipNode


def html_visit_packetdiag(self, node):
    render_dot_html(self, node, node['code'], node['options'])


def render_dot_latex(self, node, code, options, prefix='packetdiag'):
    try:
        format = self.builder.config.packetdiag_tex_image_format
        fname, outfn = get_image_filename(self, code, format, options, prefix)

        image = create_packetdiag(self, code, format, outfn, options, prefix)
        if not os.path.isfile(outfn):
            image.draw()
            image.save()

    except PacketdiagError, exc:
        self.builder.warn('dot code %r: ' % code + str(exc))
        raise nodes.SkipNode

    if fname is not None:
        self.body.append('\\par\\includegraphics{%s}\\par' % fname)
    raise nodes.SkipNode


def latex_visit_packetdiag(self, node):
    render_dot_latex(self, node, node['code'], node['options'])


def on_doctree_resolved(self, doctree, docname):
    if self.builder.name in ('gettext', 'singlehtml', 'html', 'latex', 'epub'):
        return

    for node in doctree.traverse(packetdiag):
        code = node['code']
        prefix = 'packetdiag'
        format = 'PNG'
        options = node['options']
        relfn, outfn = get_image_filename(self, code, format, options, prefix)

        image = create_packetdiag(self, code, format, outfn, options, prefix)
        if not os.path.isfile(outfn):
            image.draw()
            image.save()

        candidates = {'image/png': outfn}
        image = nodes.image(uri=outfn, candidates=candidates)
        node.parent.replace(node, image)


def setup(app):
    app.add_node(packetdiag,
                 html=(html_visit_packetdiag, None),
                 latex=(latex_visit_packetdiag, None))
    app.add_directive('packetdiag', Packetdiag)
    app.add_config_value('packetdiag_fontpath', None, 'html')
    app.add_config_value('packetdiag_fontmap', None, 'html')
    app.add_config_value('packetdiag_antialias', False, 'html')
    app.add_config_value('packetdiag_debug', False, 'html')
    app.add_config_value('packetdiag_html_image_format', 'PNG', 'html')
    app.add_config_value('packetdiag_tex_image_format', 'PNG', 'html')
    app.connect("doctree-resolved", on_doctree_resolved)
