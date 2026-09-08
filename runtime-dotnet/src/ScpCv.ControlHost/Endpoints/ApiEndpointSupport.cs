using Microsoft.AspNetCore.Http.HttpResults;
using ScpCv.Infrastructure.Auth;

namespace ScpCv.ControlHost.Endpoints;

internal static class ApiEndpointSupport
{
    public static RouteGroupBuilder RequireSessionAndCsrf(this RouteGroupBuilder group)
    {
        group.RequireAuthorization();
        group.AddEndpointFilter(
            async (context, next) =>
            {
                var method = context.HttpContext.Request.Method;
                if (HttpMethods.IsGet(method) || HttpMethods.IsHead(method) || HttpMethods.IsOptions(method))
                {
                    return await next(context).ConfigureAwait(false);
                }

                var csrf = context.HttpContext.RequestServices.GetRequiredService<CsrfTokenService>();
                var validation = csrf.Validate(context.HttpContext);
                return validation.Succeeded
                    ? await next(context).ConfigureAwait(false)
                    : Results.Json(
                        new { detail = validation.Detail, code = "csrf_failed" },
                        statusCode: StatusCodes.Status400BadRequest);
            });
        return group;
    }

    public static IResult Error(string detail, string code, int statusCode = StatusCodes.Status400BadRequest) =>
        Results.Json(new { detail, code }, statusCode: statusCode);
}
