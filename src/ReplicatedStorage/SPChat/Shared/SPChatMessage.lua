-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessageType)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local s_HttpService_0 = game:GetService("HttpService")
local v_u_9 = {
    ["ExtraDataType"] = {
        ["None"] = 0,
        ["JoinCustomChannel"] = 1,
        ["GuildInvite"] = 2
    },
    ["message_to_table"] = function(_, p5) --[[ Name: message_to_table ]] --[[ Line: 134 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        return {
            ["Message"] = p5:get_message(),
            ["SpeakerName"] = p5:get_speaker_name(),
            ["SpeakerUserId"] = p5:get_speaker_userid(),
            ["ID"] = p5:get_message_id(),
            ["ChannelID"] = p5:get_channelid(),
            ["ChannelName"] = p5:get_channel_name(),
            ["Time"] = p5:get_time(),
            ["IsFiltered"] = p5:is_filtered(),
            ["MessageType"] = p5:get_message_type(),
            ["Icon"] = p5:get_icon(),
            ["ExtraDataType"] = p5:get_extradata_type(),
            ["ExtraData"] = p5:get_extradata(),
            ["NameColor"] = v_u_4:color3_to_table(p5:get_name_color()),
            ["ChannelColor"] = v_u_4:color3_to_table(p5:get_channel_color()),
            ["MessageMetaID"] = p5:get_message_meta_id()
        };
    end,
    ["table_set_filtered_message"] = function(_, p6, p7) --[[ Name: table_set_filtered_message ]] --[[ Line: 154 ]]
        p6.Message = p7
        p6.IsFiltered = true
    end,
    ["message_to_legacy_table"] = function(_, p8) --[[ Name: message_to_legacy_table ]] --[[ Line: 199 ]]
        return {
            ["Message"] = p8:get_message(),
            ["MessageLength"] = p8:get_message_length(),
            ["FromSpeaker"] = p8:get_speaker_name(),
            ["OriginalChannel"] = p8:get_channel_name(),
            ["ChannelID"] = p8:get_channelid(),
            ["SpeakerUserId"] = p8:get_speaker_userid(),
            ["ID"] = p8:get_message_id(),
            ["MessageType"] = p8:get_message_type(),
            ["Time"] = p8:get_time(),
            ["IsFiltered"] = p8:is_filtered()
        };
    end
}
v_u_9.new = function(_, p_u_10) --[[ Name: new ]] --[[ Line: 17 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_9 ]]
    v_u_2:is_string(p_u_10)
    local v11 = {
        ["ClassName"] = "SPChatMessage"
    }
    local v_u_12 = ""
    local v_u_13 = ""
    local v_u_14 = 1
    local l_Default_0 = v_u_1.Default
    local v_u_15 = -1
    local v_u_16 = -1
    local v_u_17 = os.time()
    local v_u_18 = true
    local v_u_19 = nil
    local l_None_0 = v_u_9.ExtraDataType.None
    local v_u_20 = 0
    local v_u_21 = Color3.new(1, 1, 1)
    local v_u_22 = Color3.new(1, 1, 1)
    local v_u_23 = ""
    v11.set_speaker_name = function(p24, p25) --[[ Name: set_speaker_name ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        v_u_12 = p25
        return p24;
    end;
    v11.get_speaker_name = function(_) --[[ Name: get_speaker_name ]] --[[ Line: 48 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        return v_u_12;
    end;
    v11.set_speaker_userid = function(p26, p27) --[[ Name: set_speaker_userid ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        v_u_15 = p27
        return p26;
    end;
    v11.get_speaker_userid = function(_) --[[ Name: get_speaker_userid ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        return v_u_15;
    end;
    v11.is_speaker_default_userid = function(_) --[[ Name: is_speaker_default_userid ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        return v_u_15 == -1;
    end;
    v11.set_channel_name = function(p28, p29) --[[ Name: set_channel_name ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        v_u_13 = p29
        return p28;
    end;
    v11.get_channel_name = function(_) --[[ Name: get_channel_name ]] --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        return v_u_13;
    end;
    v11.set_channelid = function(p30, p31) --[[ Name: set_channelid ]] --[[ Line: 54 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        v_u_14 = p31
        return p30;
    end;
    v11.get_channelid = function(_) --[[ Name: get_channelid ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        return v_u_14;
    end;
    v11.set_message = function(p32, p33) --[[ Name: set_message ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): p_u_10 ]]
        p_u_10 = p33
        return p32;
    end;
    v11.get_message = function(_) --[[ Name: get_message ]] --[[ Line: 57 ]]
        --[[ Upvalues: (ref 1): p_u_10 ]]
        return p_u_10;
    end;
    v11.get_message_length = function(_) --[[ Name: get_message_length ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): p_u_10 ]]
        return #p_u_10;
    end;
    v11.set_message_id = function(p34, p35) --[[ Name: set_message_id ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        v_u_16 = p35
        return p34;
    end;
    v11.get_message_id = function(_) --[[ Name: get_message_id ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        return v_u_16;
    end;
    v11.set_message_type = function(p36, p37) --[[ Name: set_message_type ]] --[[ Line: 61 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_1, (ref 3): l_Default_0 ]]
        v_u_2:is_enum_member(p37, v_u_1)
        l_Default_0 = p37
        return p36;
    end;
    v11.get_message_type = function(_) --[[ Name: get_message_type ]] --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): l_Default_0 ]]
        return l_Default_0;
    end;
    v11.get_time = function(_) --[[ Name: get_time ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_17 ]]
        return v_u_17;
    end;
    v11.set_time = function(_, p38) --[[ Name: set_time ]] --[[ Line: 64 ]]
        --[[ Upvalues: (ref 1): v_u_17 ]]
        v_u_17 = p38
    end;
    v11.is_filtered = function(_) --[[ Name: is_filtered ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18;
    end;
    v11.set_filtered = function(p39, p40) --[[ Name: set_filtered ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18 = p40
        return p39;
    end;
    v11.set_icon = function(p41, p42) --[[ Name: set_icon ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        v_u_19 = p42
        return p41;
    end;
    v11.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 69 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        return v_u_19;
    end;
    v11.set_extradata = function(p43, p44, p45) --[[ Name: set_extradata ]] --[[ Line: 70 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_9, (ref 3): l_None_0, (ref 4): v_u_20 ]]
        v_u_2:is_enum_member(p44, v_u_9.ExtraDataType)
        l_None_0 = p44
        v_u_20 = p45
        return p43;
    end;
    v11.get_extradata_type = function(_) --[[ Name: get_extradata_type ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): l_None_0 ]]
        return l_None_0;
    end;
    v11.get_extradata = function(_) --[[ Name: get_extradata ]] --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20;
    end;
    v11.set_name_color = function(p46, p47) --[[ Name: set_name_color ]] --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21 = p47
        return p46;
    end;
    v11.get_name_color = function(_) --[[ Name: get_name_color ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21;
    end;
    v11.set_channel_color = function(p48, p49) --[[ Name: set_channel_color ]] --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        v_u_22 = p49
        return p48;
    end;
    v11.get_channel_color = function(_) --[[ Name: get_channel_color ]] --[[ Line: 77 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    v11.set_message_meta_id = function(p50, p51) --[[ Name: set_message_meta_id ]] --[[ Line: 79 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        v_u_23 = p51
        return p50;
    end;
    v11.get_message_meta_id = function(_) --[[ Name: get_message_meta_id ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23;
    end;
    return v11;
end;
v_u_9.message_from_table = function(_, p52) --[[ Name: message_from_table ]] --[[ Line: 85 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_9, (copy 4): v_u_1, (copy 5): v_u_4 ]]
    v_u_2:is_string(p52.Message)
    v_u_2:is_true(#p52.Message < v_u_3:get_chat_string_param_sanity_max_length())
    local v53 = v_u_9:new(p52.Message)
    v_u_2:is_string(p52.SpeakerName)
    v_u_2:is_true(#p52.SpeakerName < v_u_3:get_chat_string_param_sanity_max_length())
    v53:set_speaker_name(p52.SpeakerName)
    v_u_2:is_int(p52.SpeakerUserId)
    v53:set_speaker_userid(p52.SpeakerUserId)
    v_u_2:is_int(p52.ID)
    v53:set_message_id(p52.ID)
    v_u_2:is_int(p52.ChannelID)
    v53:set_channelid(p52.ChannelID)
    v_u_2:is_string(p52.ChannelName)
    v_u_2:is_true(#p52.ChannelName < v_u_3:get_chat_string_param_sanity_max_length())
    v53:set_channel_name(p52.ChannelName)
    v_u_2:is_int(p52.Time)
    v53:set_time(p52.Time)
    v_u_2:is_bool(p52.IsFiltered)
    v53:set_filtered(p52.IsFiltered)
    v_u_2:is_enum_member(p52.MessageType, v_u_1)
    v53:set_message_type(p52.MessageType)
    if p52.NameColor then
        v53:set_name_color(v_u_4:color3_from_table(p52.NameColor))
    end;
    if p52.ChannelColor then
        v53:set_channel_color(v_u_4:color3_from_table(p52.ChannelColor))
    end;
    v53:set_icon(p52.Icon)
    v53:set_extradata(p52.ExtraDataType, p52.ExtraData)
    v53:set_message_meta_id(p52.MessageMetaID)
    return v53;
end;
v_u_9.message_to_string = function(_, p54) --[[ Name: message_to_string ]] --[[ Line: 159 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): s_HttpService_0 ]]
    return s_HttpService_0:JSONEncode((v_u_9:message_to_table(p54)));
end;
v_u_9.message_from_string = function(_, p55) --[[ Name: message_from_string ]] --[[ Line: 164 ]]
    --[[ Upvalues: (copy 1): s_HttpService_0, (copy 2): v_u_9 ]]
    return v_u_9:message_from_table((s_HttpService_0:JSONDecode(p55)));
end;
v_u_9.message_from_legacy_table = function(_, p56) --[[ Name: message_from_legacy_table ]] --[[ Line: 169 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_9 ]]
    local l_Message_0 = p56.Message
    local l_MessageLength_0 = p56.MessageLength
    if l_Message_0 == nil then
        l_Message_0 = v_u_3:message_unfiltered_placeholder_of_length(l_MessageLength_0)
    end;
    local l_FromSpeaker_0 = p56.FromSpeaker
    local v57 = l_FromSpeaker_0 == nil and "System" or l_FromSpeaker_0
    local v58 = v_u_9:new(l_Message_0)
    v58:set_speaker_name(v57)
    v58:set_channel_name(p56.OriginalChannel)
    v58:set_channelid(p56.ChannelID)
    v58:set_speaker_userid(p56.SpeakerUserId)
    v58:set_message_id(p56.ID)
    v58:set_message_type(p56.MessageType)
    if typeof(p56.Time) == "number" then
        v58:set_time(p56.Time)
    end;
    v58:set_filtered(p56.IsFiltered)
    return v58;
end;
return v_u_9;
