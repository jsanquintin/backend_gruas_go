export type Kind = 'delivery' | 'roadside';
export type Status = 'pending' | 'assigned' | 'en_route' | 'on_site' | 'completed' | 'canceled';
export type Role = 'admin' | 'dispatcher' | 'merchant' | 'driver';
export interface ServiceEvent {id:number; actor_id:number; event_type:string; detail:string; created_at:string}
export interface Service {lat:string|null;lng:string|null;destination_lat:string|null;destination_lng:string|null;recipient_name:string|null;recipient_phone:string|null;package_description:string|null;vehicle_plate:string|null;vehicle_description:string|null;id:number;code:string;kind:Kind;service_type:string;status:Status;operator_id:number|null;customer_name:string;customer_phone:string;pickup_address:string;destination_address:string|null;quoted_total_dop:string|null;operator_fee_dop:string|null;notes:string|null;proof_note:string|null;created_at:string;events:ServiceEvent[]}
export interface Operator {verification_status:'pending'|'approved'|'rejected'|'suspended';license_number:string|null;license_expires_on:string|null;registration_reference:string|null;insurance_policy:string|null;insurance_expires_on:string|null;verification_note:string|null;verified_by:number|null;verified_at:string|null;id:number;name:string;phone:string;kind:Kind;vehicle_type:string;license_plate:string|null;user_id:number|null;verified:boolean;active:boolean}
export interface Dashboard {total:number;pending:number;active:number;completed:number;canceled:number;delivery:number;roadside:number}
export interface User {id:number;name:string;email:string;role:Role}

export interface OperatorReview {id:number;actor_id:number;action:string;note:string;created_at:string}

export interface Position {operator_id:number;name:string;kind:Kind;lat:string;lng:string;accuracy_m:number;recorded_at:string;online:boolean;available:boolean}
export interface Tariff {id:number;kind:Kind;service_type:string;base_dop:string;per_km_dop:string;minimum_dop:string;operator_base_dop:string;active:boolean;updated_at:string}
export interface Estimate {service_type:string;mode:string;distance_km:string|null;suggested_total_dop:string;suggested_operator_fee_dop:string;warning:string}
