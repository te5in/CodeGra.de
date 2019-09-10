import { CgMarkdownIt } from '@/cg-math';

describe('CgMarkdownIt', () => {
    let md;
    beforeEach(() => {
        md = new CgMarkdownIt();
    });

    it('should work without any math', () => {
        expect(md.render('Hello').trimRight()).toEqual('<p>Hello</p>');
    });

    it('should render simple math', () => {
        expect(md.render('Dit is some math: $hello$').trimRight())
            .toEqual('<p>Dit is some math: $hello$</p>');
    });

    it('should work with multiple math things', () => {
        expect(md.render('Dit is some math: $hello$, and some more: $\\textbf{5}$').trimRight())
            .toEqual('<p>Dit is some math: $hello$, and some more: $\\textbf{5}$</p>');
    });

    it('should work with at signs', () => {
        expect(md.render('@one@ @@2@@ @@@three@@@ @@@@four@@@@ @@@@even$#@$').trimRight())
            .toEqual('<p>@one@ @@2@@ @@@three@@@ @@@@four@@@@ @@@@even$#@$</p>');
    });

    it('should work with begin', () => {
        expect(md.render('\\begin{a}\nHello\n\\end{a}').trimRight())
            .toEqual('<p>\\begin{a}\nHello\n\\end{a}</p>');
    });

    it('should work with \\\\(\\\\)', () => {
        expect(md.render('\\\\(1 + `1\'\\\\)').trimRight())
            .toEqual('<p>\\(1 + &#96;1&#39;\\)</p>');
    });

    it('should work with \\\\[\\\\]', () => {
        expect(md.render('\\\\[1 + `1\'\\\\]').trimRight())
            .toEqual('<p>\\[1 + &#96;1&#39;\\]</p>');
    });

    it('\\(\\) should not render math', () => {
        expect(md.render('\\(1\\)').trimRight())
            .toEqual('<p>(1)</p>');
    })

    it('should work as expected with inline code', () => {
        expect(md.render('`print(5)`').trimRight())
            .toEqual('<p><code>print(5)</code></p>');
    });

    it('should not render math with multiple newlines', () => {
        expect(md.render('\\begin{a}\n\n5\n\\end{a}').trimRight())
            .toEqual('<p>\\begin{a}</p>\n<p>5\n\\end{a}</p>');
    });

    it('nested blocks work', () => {
        expect(md.render('\\\\begin{a}\\\\begin{a}d\\\\end{a}\\\\end{a}').trimRight())
            .toEqual('<p>\\begin{a}\\\\begin{a}\d\\\\end{a}\\end{a}</p>');
    });

    it('should work with braces', () => {
        const txt = `\\\\begin{align}
{
hello
\\\\end{align}


}
\\\\end{align}`;
        // This output is exactly the same as ipython generates
        expect(md.render(txt)).toEqual(`<p>\\begin{align}
{
hello
\\\\end{align}</p>
<p>}
\\end{align}</p>
`);
    });

    it('should be possible to disable math', () => {
        const txt ='\\\\begin{a}5\n\\\\end{a}';
        expect(md.render(txt, true).trimRight()).toEqual(`<p>\\begin{a}5\n\\end{a}</p>`);
    });

    it('should work with code containing dollar signs', () => {
        expect(md.render('`$foo` and `$bar` are variables').trimRight())
            .toEqual('<p><code>$foo</code> and <code>$bar</code> are variables</p>');
    });

    it('should work with unbalanced braces', () => {
        expect(md.render('\\\\begin{align} { d \\\\end{align}').trimRight())
            .toEqual('<p>\\begin{align} { d \\\\end{align}</p>');
    });

    it('should escape correctly with \\b', () => {
        expect(md.render('\bhello')).toEqual('<p>\bhello</p>\n');
    });
});
