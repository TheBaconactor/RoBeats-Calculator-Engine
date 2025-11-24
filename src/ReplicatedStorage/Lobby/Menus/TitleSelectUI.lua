-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:40 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_5 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v7 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_8 = nil
v7:require_client(function() --[[ Line: 12 ]]
    --[[ Upvalues: (ref 1): v_u_8 ]]
    v_u_8 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
end)
return {
    ["new"] = function(_, p_u_9, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_6, (ref 4): v_u_8, (copy 5): v_u_1, (copy 6): v_u_5, (copy 7): v_u_3 ]]
        local function f_get_available_titles() --[[ Name: get_available_titles ]] --[[ Line: 19 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2, (ref 3): v_u_4, (ref 4): v_u_6 ]]
            local v12 = p_u_9._player_blob_manager:get_player_blob()
            local v13 = v_u_2:new()
            v13:push_back(v_u_4:singleton():get_default_title())
            for v14 = 1, #v12.OwnedTitles do
                v13:push_back(v_u_4:singleton():get_title_for_id(v12.OwnedTitles[v14].ID))
            end;
            if v_u_6:playerblob_has_vip_for_current_day(v12, p_u_9:get_current_dayid()) then
                for v15, _ in v_u_6:get_vip_title_ids_set():key_itr() do
                    v13:push_back(v_u_4:singleton():get_title_for_id(v15))
                end;
            end;
            if p_u_9._guild_manager:player_has_guild() then
                v13:push_back(v_u_4:singleton():get_title_for_id(v_u_4:singleton():get_guild_title_id()))
            end;
            v13:sort(function(p16, p17) --[[ Line: 40 ]]
                return p16:get_title_id() < p17:get_title_id();
            end)
            return v13;
        end;
        local l_CurrentTitleID_0 = p_u_9._player_blob_manager:get_player_blob().CurrentTitleID
        local v27 = v_u_8:new(p_u_9, p_u_10, p_u_11, function(p18) --[[ Line: 55 ]]
            --[[ Upvalues: (copy 1): f_get_available_titles ]]
            p18:set_header_text("Select title to use...")
            p18:get_element_list():push_back_from_list((f_get_available_titles()))
            p18:set_sub_text(string.format("Owned titles: %d", p18:get_element_list():count() - 1))
        end, function(p19, p20, p21, _, p22) --[[ Line: 63 ]]
            --[[ Upvalues: (copy 1): l_CurrentTitleID_0, (ref 2): v_u_1 ]]
            if p19 then
                p20.Text = p19:get_name()
                p20.TextColor3 = p19:get_color()
                if p19:get_title_id() == l_CurrentTitleID_0 then
                    p20.Text = "[Selected] " .. p20.Text
                    p21.Image = v_u_1:important_assetid()
                else
                    p21.Image = v_u_1:get_question_assetid()
                end;
                p22:get_description_display().Text = p19:get_description()
            end;
        end, function(p23) --[[ Line: 78 ]]
            --[[ Upvalues: (copy 1): l_CurrentTitleID_0, (copy 2): p_u_11, (ref 3): v_u_5, (copy 4): p_u_9, (copy 5): p_u_10, (ref 6): v_u_3 ]]
            if p23 ~= nil then
                local v_u_24 = p23:get_title_id()
                if l_CurrentTitleID_0 ~= v_u_24 then
                    local v_u_25 = p_u_11:push_menu(v_u_5:new(p_u_9, p_u_10, p_u_11):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
                    p_u_9._evt:wait_on_event_once(v_u_3.EVT_PlayerBlob_ServerSetTitleResponse, function(p26) --[[ Line: 84 ]]
                        --[[ Upvalues: (ref 1): p_u_11, (copy 2): v_u_25, (ref 3): v_u_5, (ref 4): p_u_9, (ref 5): p_u_10, (copy 6): v_u_24 ]]
                        if p26 == true then
                            p_u_9._player_blob_manager:do_sync(function() --[[ Line: 97 ]]
                                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_25 ]]
                                p_u_11:remove_menu(v_u_25)
                            end)
                        else
                            p_u_11:remove_menu(v_u_25)
                            p_u_11:push_menu(v_u_5:new(p_u_9, p_u_10, p_u_11):set_text("Error", string.format("Title set failed title_id(%s)", (tostring(v_u_24)))))
                        end;
                    end)
                    p_u_9._evt:fire_event_to_server(v_u_3.EVT_PlayerBlob_ClientSetTitle, v_u_24)
                end;
            end;
        end)
        local v28 = v27:get_list_adapter()
        v28:set_do_wrap(true)
        v28:go_to_page(v28:get_page_of_element(v_u_4:singleton():get_title_for_id(l_CurrentTitleID_0)))
        return v27;
    end
};
