from copy import deepcopy

import jsonschema


def validate_discriminator(validator, discriminator, instance, schema):
    # Short-circuit validation for non-dict instances which cannot be validated
    # against an object schema. In this case, subsequent validators (allOf)
    # should fail.
    if not isinstance(instance, dict):
        return

    if not instance.get(discriminator):
        # This should raise a validation error from jsonschema as the
        # discrminator is a required field.
        return

    if instance[discriminator] not in validator.schema['definitions']:
        yield jsonschema.ValidationError(
            "{} is not a valid {} for discriminator".format(
                instance[discriminator],
                discriminator,
            ),
            path=(discriminator, )
        )
        return
    else:
        definition = deepcopy(
            validator.schema['definitions'][instance[discriminator]]
        )

        # Generally, for objects with discriminators, we have a list of
        # property schemas. E.g. CandyItem includes allOf with Item and
        # the CandyItem's properties. If we re-apply validation using
        # the discriminated schema, it will recursively re-evaluate
        # the parent schema. This is inelegant, but jsonschema wasn't
        # designed with this in mind.
        def _clear_discriminators(definition):
            if definition.get('allOf'):
                for index, spec in enumerate(definition['allOf']):
                    if 'discriminator' in spec:
                        # If the current spec has a discriminator, pop it.
                        definition['allOf'].pop(index)
                    _clear_discriminators(definition['allOf'][index])
            if 'discriminator' in definition:
                definition.pop('discriminator')
        _clear_discriminators(definition)

        for error in validator.iter_errors(instance, definition):
            # Workaround for the required validator not being attached to
            # a field name.
            if error.validator == 'required':
                yield jsonschema.ValidationError(
                    error.message,
                    path=error.path,
                )
            else:
                yield error


def validator_required(validator, required, instance, schema):
    if not validator.is_type(instance, "object"):
        return
    for property in required:
        if property not in instance:
            yield jsonschema.ValidationError(
                "%r is a required property" % property,
                path=[property],
            )

#: Extends the Draft4Validator with support for discriminators
SwaggerValidator = jsonschema.validators.extend(
    jsonschema.Draft4Validator,
    validators={
        "discriminator": validate_discriminator,
        "required": validator_required,
    },
)
