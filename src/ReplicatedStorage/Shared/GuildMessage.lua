-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_27 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        local v3 = {}
        local v_u_4 = -1
        local v_u_5 = ""
        local v_u_6 = os.time()
        local v_u_7 = ""
        local v_u_8 = ""
        v3.has_player_id = function(_) --[[ Name: has_player_id ]] --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            return v_u_4 >= 0;
        end;
        v3.set_player_id_name = function(p9, p10, p11) --[[ Name: set_player_id_name ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_4, (ref 3): v_u_5 ]]
            v_u_2:is_int(p10)
            v_u_2:is_string(p11)
            if #p11 > 4096 then
                p11 = string.sub(p11, 1, 4096) .. "..."
            end;
            v_u_4 = p10
            v_u_5 = p11
            return p9;
        end;
        v3.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            return v_u_4;
        end;
        v3.get_player_name = function(_) --[[ Name: get_player_name ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            return v_u_5;
        end;
        v3.set_message_time = function(p12, p13) --[[ Name: set_message_time ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_6 ]]
            v_u_2:is_number(p13)
            v_u_6 = p13
            return p12;
        end;
        v3.get_message_time = function(_) --[[ Name: get_message_time ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            return v_u_6;
        end;
        v3.has_override_icon = function(_) --[[ Name: has_override_icon ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return #v_u_7 > 0;
        end;
        v3.set_override_icon = function(p14, p15) --[[ Name: set_override_icon ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            if #p15 > 4096 then
                p15 = string.sub(p15, 1, 4096) .. "..."
            end;
            v_u_7 = p15
            return p14;
        end;
        v3.get_override_icon = function(_) --[[ Name: get_override_icon ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7;
        end;
        v3.set_message_text = function(p16, p17) --[[ Name: set_message_text ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            local v18
            if #p17 > 4096 then
                v18 = string.sub(p17, 1, 4096) .. "..."
            else
                v18 = p17
            end;
            v_u_8 = v18
            v_u_8 = p17
            return p16;
        end;
        v3.get_message_text = function(_) --[[ Name: get_message_text ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8;
        end;
        local v_u_19 = nil
        v3.bind_local_extra_data = function(p20, p21) --[[ Name: bind_local_extra_data ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            v_u_19 = p21
            return p20;
        end;
        v3.get_local_extra_data = function(_) --[[ Name: get_local_extra_data ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        v3.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): v_u_7, (ref 5): v_u_8 ]]
            return {
                ["PlayerID"] = v_u_4,
                ["PlayerName"] = v_u_5,
                ["MessageTime"] = v_u_6,
                ["OverrideIcon"] = v_u_7,
                ["MessageText"] = v_u_8
            };
        end;
        return v3;
    end,
    ["list_to_table"] = function(_, p22) --[[ Name: list_to_table ]] --[[ Line: 92 ]]
        local v23 = {}
        for v24 = 1, p22:count() do
            table.insert(v23, p22:get(v24):to_table())
        end;
        return v23;
    end,
    ["get_message_text_with_cutoff_length"] = function(_, p25, p26) --[[ Name: get_message_text_with_cutoff_length ]] --[[ Line: 100 ]]
        if p26 < #p25 then
            p25 = string.sub(p25, 1, p26) .. "..."
        end;
        return p25;
    end
}
local function _(p28) --[[ Name: verify_input_string_length ]] --[[ Line: 7 ]]
    if #p28 > 4096 then
        return string.sub(p28, 1, 4096) .. "...";
    else
        return p28;
    end;
end;
v_u_27.from_table = function(_, p29) --[[ Name: from_table ]] --[[ Line: 74 ]]
    --[[ Upvalues: (copy 1): v_u_27 ]]
    local v30 = v_u_27:new()
    if p29.PlayerID ~= nil and p29.PlayerName ~= nil then
        v30:set_player_id_name(p29.PlayerID, p29.PlayerName)
    end;
    if p29.MessageTime then
        v30:set_message_time(p29.MessageTime)
    end;
    if p29.OverrideIcon then
        v30:set_override_icon(p29.OverrideIcon)
    end;
    if p29.MessageText then
        v30:set_message_text(p29.MessageText)
    end;
    return v30;
end;
v_u_27.table_to_list = function(_, p31) --[[ Name: table_to_list ]] --[[ Line: 84 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_27 ]]
    local v32 = v_u_1:new()
    for v33 = 1, #p31 do
        v32:push_back(v_u_27:from_table(p31[v33]))
    end;
    return v32;
end;
return v_u_27;
