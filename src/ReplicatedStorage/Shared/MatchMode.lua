-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:09 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_1 = {
    ["Compete"] = 1,
    ["Casual"] = 2
}
v_u_1.get_icon_for_mode = function(_, p2) --[[ Name: get_icon_for_mode ]] --[[ Line: 8 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p2 == v_u_1.Compete and "rbxassetid://6971830223" or "rbxassetid://6971830088";
end;
v_u_1.get_description_for_mode = function(_, p3) --[[ Name: get_description_for_mode ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p3 == v_u_1.Compete and "Gear power will be included in score. Scores will be used for missions and leaderboards." or "Gear power will not be included in score or match placement.";
end;
local l_Compete_0 = v_u_1.Compete
v_u_1.get_selected_mode = function(_) --[[ Name: get_selected_mode ]] --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): l_Compete_0 ]]
    return l_Compete_0;
end;
v_u_1.set_selected_mode = function(_, p4) --[[ Name: set_selected_mode ]] --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): l_Compete_0 ]]
    l_Compete_0 = p4
end;
v_u_1.get_server_game_instance_player_score = function(_, p5) --[[ Name: get_server_game_instance_player_score ]] --[[ Line: 28 ]]
    --[[ Upvalues: (ref 1): l_Compete_0, (copy 2): v_u_1 ]]
    if l_Compete_0 == v_u_1.Compete then
        return p5._score;
    else
        return p5._naked_score;
    end;
end;
v_u_1.get_server_game_instance_player_chain = function(_, p6) --[[ Name: get_server_game_instance_player_chain ]] --[[ Line: 36 ]]
    --[[ Upvalues: (ref 1): l_Compete_0, (copy 2): v_u_1 ]]
    if l_Compete_0 == v_u_1.Compete then
        return p6._chain;
    else
        return p6._naked_chain;
    end;
end;
v_u_1.get_server_game_instance_player_powerbar_active = function(_, p7) --[[ Name: get_server_game_instance_player_powerbar_active ]] --[[ Line: 44 ]]
    --[[ Upvalues: (ref 1): l_Compete_0, (copy 2): v_u_1 ]]
    if l_Compete_0 == v_u_1.Compete then
        return p7._power_bar_active;
    else
        return p7._naked_power_bar_active;
    end;
end;
return v_u_1;
