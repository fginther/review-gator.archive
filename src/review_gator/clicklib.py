from click import Option, UsageError


class NotRequiredIf(Option):
    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop('mutually_exclusive', []))
        help = kwargs.get('help', '')
        if self.mutually_exclusive:
            ex_str = ', '.join(self.mutually_exclusive)
            kwargs['help'] = "{} NOTE: This argument is mutually exclusive " \
                             "with arguments: [{}].".format(help, ex_str)

        super(NotRequiredIf, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        we_are_present = self.name in opts
        other_present = self.mutually_exclusive.intersection(opts)
        if self.required and other_present:
            if we_are_present:
                raise UsageError(
                        "Illegal usage: `{}` is mutually exclusive with "
                        "arguments `{}`.".format(
                                self.name,
                                ', '.join(self.mutually_exclusive)
                        )
                )
            else:
                self.required = False

        return super(NotRequiredIf, self).handle_parse_result(
            ctx,
            opts,
            args
        )
