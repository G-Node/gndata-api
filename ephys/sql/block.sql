--drop schema public cascade;
--create schema public;

ALTER TABLE ephys_spiketrain DROP CONSTRAINT ephys_spiketrain_pkey CASCADE;
ALTER TABLE ephys_spiketrain ADD PRIMARY KEY (guid);

ALTER TABLE ephys_analogsignalarray DROP CONSTRAINT ephys_analogsignalarray_pkey CASCADE;
ALTER TABLE ephys_analogsignalarray ADD PRIMARY KEY (guid);

ALTER TABLE ephys_analogsignal DROP CONSTRAINT ephys_analogsignal_pkey CASCADE;
ALTER TABLE ephys_analogsignal ADD PRIMARY KEY (guid);

ALTER TABLE ephys_irregularlysampledsignal DROP CONSTRAINT ephys_irregularlysampledsignal_pkey CASCADE;
ALTER TABLE ephys_irregularlysampledsignal ADD PRIMARY KEY (guid);

ALTER TABLE ephys_spike DROP CONSTRAINT ephys_spike_pkey CASCADE;
ALTER TABLE ephys_spike ADD PRIMARY KEY (guid);

ALTER TABLE ephys_eventarray DROP CONSTRAINT ephys_eventarray_pkey CASCADE;
ALTER TABLE ephys_eventarray ADD PRIMARY KEY (guid);

ALTER TABLE ephys_event DROP CONSTRAINT ephys_event_pkey CASCADE;
ALTER TABLE ephys_event ADD PRIMARY KEY (guid);

ALTER TABLE ephys_epocharray DROP CONSTRAINT ephys_epocharray_pkey CASCADE;
ALTER TABLE ephys_epocharray ADD PRIMARY KEY (guid);

ALTER TABLE ephys_epoch DROP CONSTRAINT ephys_epoch_pkey CASCADE;
ALTER TABLE ephys_epoch ADD PRIMARY KEY (guid);

ALTER TABLE ephys_recordingchannel DROP CONSTRAINT ephys_recordingchannel_pkey CASCADE;
ALTER TABLE ephys_recordingchannel ADD PRIMARY KEY (guid);

ALTER TABLE ephys_unit DROP CONSTRAINT ephys_unit_pkey CASCADE;
ALTER TABLE ephys_unit ADD PRIMARY KEY (guid);

ALTER TABLE ephys_segment DROP CONSTRAINT ephys_segment_pkey CASCADE;
ALTER TABLE ephys_segment ADD PRIMARY KEY (guid);

ALTER TABLE ephys_recordingchannelgroup DROP CONSTRAINT ephys_recordingchannelgroup_pkey CASCADE;
ALTER TABLE ephys_recordingchannelgroup ADD PRIMARY KEY (guid);

ALTER TABLE ephys_block DROP CONSTRAINT ephys_block_pkey CASCADE;
ALTER TABLE ephys_block ADD PRIMARY KEY (guid);

