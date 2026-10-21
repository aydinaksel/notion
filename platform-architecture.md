# Platform Architecture

The Plum "monolith" is the `plumguide/plum` repo (`Plum.Web`, `Plum.Domain`,
`Plum.Monolith.Domain`). "Plumpy CMS" is the same system: its CMS app, `Plum.Web.Cms`.
The platform is mostly split into microservices under the `plumguide` GitHub org, but
not entirely: user and account lifecycle events, and `AbandonedSearchEmailSent`, are
still emitted by the monolith.

Salesforce integrates with the platform only through `plum-api` (`api.plumguide.com`).
Apex (`SaveAndSyncPropertiesCX_Daf`, `ChaseCollectionCalloutService`) calls `plum-api`,
which forwards host upserts to the monolith and seeds `listing-service` /
`integration-service`. Salesforce never calls `salesforce-service` directly.
`salesforce-service` is the write-back path: it consumes Service Bus events and writes
Salesforce, and reads Salesforce over SOQL for dedup, but Salesforce does not push to it.

When tracing which service publishes a Service Bus event, do not assume an event is
monolith-owned just because its class exists in `plum`. Legacy domain classes are
duplicated into the services that took them over: booking events exist in both `plum`
and `checkout-service`, but `checkout-service` is the live publisher. Verify the actual
publish site (`mediator.Publish`, `_eventBus.Send`, `AddMessage`), not the class
definition.

Salesforce write lineage is documented across two Operations Manual pages: the
Salesforce-side view on `Salesforce Data Lineage` (`System = Salesforce`) and the
platform event-source view on `salesforce-service` (`System = Platform`).
