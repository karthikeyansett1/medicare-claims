select 'calendar' as failure from {{ ref('dim_date') }}
having count(*) <> (max(date)-min(date)+1)
 or min(date) > date '2008-01-01' or max(date) < date '2010-12-31'
 or count(*) filter(where is_analysis_window) <> 1096
