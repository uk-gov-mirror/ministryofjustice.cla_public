(function () {
  'use strict';

  moj.Modules.FormErrors = {
    init: function() {
      this.bindEvents();
      this.loadTemplates();
    },

    bindEvents: function() {
      $('button[type="submit"]', $('form')).on('click',  $.proxy(this.postToFormErrors, this));
    },

    postToFormErrors: function(e) {
      this.clearErrors();
      this.$form = $(e.currentTarget).closest('form');
      if (this.$form.length) {
        e.preventDefault();
        e.stopPropagation();
        $.ajax({
          type: 'OPTIONS',
          url: '',
          contentType: 'application/x-www-form-urlencoded',
          data: this.$form.serialize()
        }).done(
          $.proxy(this.onAjaxSuccess, this)
        ).fail(
          $.proxy(this.onAjaxError, this)
        );
      }
    },

    onAjaxSuccess: function (errors) {
      if (!$.isEmptyObject(errors)) {
        this.loadErrors(errors);
        $('html, body').animate({
            scrollTop: $('.alert-error:visible:first').offset().top - 50
        }, 300);
      } else {
        this.$form.submit();
      }
    },

    onAjaxError: function () {
      this.$form.submit();
    },

    formatErrors: function (errors) {
      var errorFields = {};

      (function fieldName (errorsObj, prefix) {
        prefix = (typeof prefix === 'undefined')? '': prefix + '-';
        for (var key in errorsObj) {
          var field = prefix + key;
          if ($.isArray(errorsObj[key])) {
            errorFields[field] = errorsObj[key];
          } else {
            fieldName(errorsObj[key], field);
          }
        }
      })(errors);

      return errorFields;
    },

    loadErrors: function (errors) {
      var errorFields = this.formatErrors(errors);
      var self = this;

      function addErrors(errors, fieldName) {
        if (_.isString(errors[0])) {
          $('#field-' + fieldName).addClass('m-error');
          $('#field-label-' + fieldName)
            .addClass('m-error')
            .after(self.fieldError({ errors: errors }));
        } else if(_.isObject(errors[0]) && !_.isArray(errors[0])) {
          // Multiple forms (e.g. properties)
          _.each(errors, function(errors, i) {
            _.each(errors, function(subformErrors, subformFieldName) {
              addErrors(subformErrors, fieldName + '-' + i + '-' + subformFieldName);
            });
          });
        } else {
          _.each(errors, function(subformErrors) {
            addErrors(subformErrors[1], fieldName + '-' + subformErrors[0]);
          });
        }
      }

      _.each(errorFields, addErrors);

      this.$form.prepend(this.mainFormError());
    },

    loadTemplates: function () {
      this.mainFormError = _.template($('#mainFormError').html());
      this.fieldError = _.template($('#fieldError').html());
    },

    clearErrors: function () {
      $('.form-row.field-error').remove();
      $('.alert.alert-error').remove();
      $('.m-error').removeClass('m-error');
    }
  };
}());
