-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:47 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Shared.GuildData)
local v_u_4 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
local v_u_5 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v6 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_7 = nil
v6:require_client(function() --[[ Line: 17 ]]
    --[[ Upvalues: (ref 1): v_u_7 ]]
    v_u_7 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
return {
    ["show_recruiting_teams_ui"] = function(_, p_u_8, p_u_9, p_u_10) --[[ Name: show_recruiting_teams_ui ]] --[[ Line: 23 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_3, (copy 6): v_u_5 ]]
        local v_u_11 = p_u_8._menus:push_menu(v_u_7:new(p_u_8, p_u_8._spui, p_u_8._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_8._evt:wait_on_event_once(v_u_2.EVT_GuildRecruitment_GetRecruitmentData_ServerResponse, function(p12, p13, p_u_14, p15) --[[ Line: 26 ]]
            --[[ Upvalues: (copy 1): p_u_8, (copy 2): v_u_11, (ref 3): v_u_1, (copy 4): p_u_10, (ref 5): v_u_4, (copy 6): p_u_9, (ref 7): v_u_3, (ref 8): v_u_5, (ref 9): v_u_7, (ref 10): v_u_2 ]]
            p_u_8._menus:remove_menu(v_u_11)
            local v_u_16 = v_u_1:new()
            if typeof(p15) == "table" then
                v_u_16:add_set_from_table_list(p15)
            end;
            if p12 == false then
                p_u_8._menus:push_menu(v_u_7:new(p_u_8, p_u_8._spui, p_u_8._menus):set_text("Failed", p13))
            else
                local v_u_17 = nil
                v_u_17 = p_u_10:push_menu(v_u_4:new(p_u_8, p_u_9, p_u_10, function(p18) --[[ Line: 37 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_14 ]]
                    p18:set_header_text("Join a Team")
                    p18:set_sub_text("If there are any recruiting teams on your current server, you can request to join them.")
                    p18:get_element_list():set_table(v_u_3:table_list_to_list(p_u_14):get_table())
                end, function(p19, p20, p21, _, p22) --[[ Line: 44 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_5, (copy 3): v_u_16 ]]
                    p20.Text = p19:get_name()
                    p21.Image = p19:get_icon()
                    local v23 = "-"
                    for _, v24 in p19:get_member_infos():key_itr() do
                        if v_u_3:player_has_admin_access(p19, v24:get_rbxid()) then
                            v23 = v24:get_name()
                            break;
                        end;
                    end;
                    p22:get_description_display().Text = string.format("Admin: %s Members: %d/%d Recruiting: %s", v23, p19:get_total_members(), v_u_5:get_max_guild_players(), v_u_3:get_recruitment_state_name(p19:get_recruitment_state()))
                    p22:set_select_button_enabled(true)
                    if v_u_16:contains(p19:get_guildid()) then
                        p20.Text = p20.Text .. " (Sent)"
                        p22:set_select_button_enabled(false)
                    end;
                end, function(p25) --[[ Line: 70 ]]
                    --[[ Upvalues: (copy 1): v_u_16, (ref 2): p_u_8, (ref 3): v_u_7, (ref 4): v_u_2, (ref 5): v_u_17 ]]
                    if p25 ~= nil then
                        v_u_16:add_set(p25:get_guildid())
                        local v_u_26 = p_u_8._menus:push_menu(v_u_7:new(p_u_8, p_u_8._spui, p_u_8._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                        p_u_8._evt:wait_on_event_once(v_u_2.EVT_GuildRecruitment_AddRecruitmentRequest_ServerResponse, function(_, p27, p28) --[[ Line: 74 ]]
                            --[[ Upvalues: (ref 1): p_u_8, (copy 2): v_u_26, (ref 3): v_u_7, (ref 4): v_u_17 ]]
                            p_u_8._menus:remove_menu(v_u_26)
                            p_u_8._menus:push_menu(v_u_7:new(p_u_8, p_u_8._spui, p_u_8._menus):set_text("Sent", p27))
                            if p28 then
                                p_u_8._menus:remove_menu(v_u_17)
                            end;
                        end)
                        p_u_8._evt:fire_event_to_server(v_u_2.EVT_GuildRecruitment_AddRecruitmentRequest_Client, p25:get_guildid())
                    end;
                end):set_empty_message("No recruiting teams on your current server. Check back later."):set_close_on_element_select(false))
            end;
        end)
        p_u_8._evt:fire_event_to_server(v_u_2.EVT_GuildRecruitment_GetRecruitmentData_Client)
    end
};
