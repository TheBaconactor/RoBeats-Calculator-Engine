-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:41 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
local v_u_16 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v_u_18 = require(game.ReplicatedStorage.Shared.GuildMessage)
require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_19 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_20 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v21 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
local v_u_26 = nil
v21:require_client(function() --[[ Line: 32 ]]
    --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_23, (ref 3): v_u_24, (ref 4): v_u_25, (ref 5): v_u_26 ]]
    v_u_22 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.PreviewCharacterUI)
    v_u_24 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_25 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_26 = require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
end)
local v_u_35 = {
    ["webnpc_do_like"] = function(_, p_u_27, p_u_28, p_u_29) --[[ Name: webnpc_do_like ]] --[[ Line: 419 ]]
        --[[ Upvalues: (ref 1): v_u_22, (copy 2): v_u_9, (copy 3): v_u_8 ]]
        if p_u_27._player_blob_manager:get_liked_web_npc_id_set():contains(p_u_28:get_webnpcid()) then
            return p_u_29();
        end;
        local v_u_30 = p_u_27._menus:push_menu(v_u_22:new(p_u_27, p_u_27._spui, p_u_27._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_27._evt:wait_on_event_once(v_u_9.EVT_WebNPC_ServerLikeNPCResponse, function(p_u_31, p_u_32, p_u_33, p34) --[[ Line: 423 ]]
            --[[ Upvalues: (copy 1): p_u_27, (copy 2): v_u_30, (ref 3): v_u_22, (copy 4): p_u_28, (copy 5): p_u_29, (ref 6): v_u_8 ]]
            local function f_fin() --[[ Name: fin ]] --[[ Line: 424 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_30, (copy 3): p_u_33, (copy 4): p_u_31, (ref 5): v_u_22, (copy 6): p_u_32, (ref 7): p_u_28, (ref 8): p_u_29, (ref 9): v_u_8 ]]
                p_u_27._menus:remove_menu(v_u_30)
                if typeof(p_u_33) == "table" then
                    p_u_27._player_blob_manager:get_liked_web_npc_id_set():add_set_from_table_list(p_u_33)
                end;
                if p_u_31 then
                    p_u_28:set_like_count(p_u_28:get_like_count() + 1)
                else
                    p_u_27._menus:push_menu(v_u_22:new(p_u_27, p_u_27._spui, p_u_27._menus):set_text("Error", p_u_32))
                end;
                p_u_29()
                p_u_27._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
            end;
            if p34 == true then
                p_u_27._player_blob_manager:do_sync(function() --[[ Line: 439 ]]
                    --[[ Upvalues: (copy 1): f_fin ]]
                    f_fin()
                end)
            else
                f_fin()
            end;
        end)
        p_u_27._evt:fire_event_to_server(v_u_9.EVT_WebNPC_ClientLikeNPC, p_u_28:get_webnpcid())
    end
}
local function _() --[[ Name: get_submit_placeholder_text ]] --[[ Line: 42 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return v_u_3:new():push_back_table_list({
        "I couldn\'t think a message so here I am!",
        "Rather be playing robeats right now...",
        "trade boosts pls",
        "give stars pls",
        "Insight is the best map"
    }):random();
end;
local v_u_36 = v_u_2:new({
    [v_u_12.Tiers.Tier1] = "Message Only",
    [v_u_12.Tiers.Tier2] = "Message and Coin Gift",
    [v_u_12.Tiers.Tier3] = "Message and Star Gift"
})
local l_SELECTED_DANCE_RANDOM_0 = v_u_12.SELECTED_DANCE_RANDOM
v_u_35.new = function(_, p_u_37, p_u_38, p_u_39) --[[ Name: new ]] --[[ Line: 60 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_12, (copy 4): v_u_15, (ref 5): l_SELECTED_DANCE_RANDOM_0, (copy 6): v_u_1, (copy 7): v_u_10, (copy 8): v_u_6, (copy 9): v_u_5, (copy 10): v_u_8, (ref 11): v_u_22, (copy 12): v_u_14, (copy 13): v_u_36, (copy 14): v_u_35, (copy 15): v_u_11, (copy 16): v_u_3, (copy 17): v_u_13, (copy 18): v_u_7, (ref 19): v_u_24, (copy 20): v_u_16, (copy 21): v_u_17, (ref 22): v_u_23 ]]
    local v_u_40 = v_u_4:new(p_u_38, p_u_39)
    local v_u_41 = nil
    local v_u_42 = 1
    local v_u_43 = 1
    local v_u_44 = v_u_2:new()
    local l_Tier1_0 = v_u_12.Tiers.Tier1
    local function _() --[[ Name: update_selected_tier ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): v_u_44, (ref 2): l_Tier1_0 ]]
        for v45, v46 in v_u_44:key_itr() do
            v46:set_toggle(v45 == l_Tier1_0)
        end;
    end;
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = nil
    local function f_update_selected_dance_display() --[[ Name: update_selected_dance_display ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): v_u_15, (ref 2): l_SELECTED_DANCE_RANDOM_0, (ref 3): v_u_47, (ref 4): v_u_48, (ref 5): v_u_1 ]]
        if v_u_15:singleton():contains_dance_for_id(l_SELECTED_DANCE_RANDOM_0) then
            v_u_47.Text = v_u_15:singleton():get_dance_name_for_id(l_SELECTED_DANCE_RANDOM_0)
            v_u_48.Image = v_u_15:singleton():get_dance_icon_for_id(l_SELECTED_DANCE_RANDOM_0)
        else
            v_u_47.Text = "Random"
            v_u_48.Image = v_u_1:get_question_assetid()
        end;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 90 ]]
        --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_1, (ref 3): v_u_10, (copy 4): v_u_40, (copy 5): p_u_37, (ref 6): v_u_6, (ref 7): v_u_5, (copy 8): p_u_38, (copy 9): p_u_39, (ref 10): v_u_8, (ref 11): v_u_22, (ref 12): v_u_2, (ref 13): v_u_12, (ref 14): v_u_14, (ref 15): v_u_36, (copy 16): v_u_44, (ref 17): l_Tier1_0, (ref 18): v_u_35, (ref 19): v_u_49, (ref 20): v_u_11, (ref 21): v_u_47, (ref 22): v_u_48, (copy 23): f_update_selected_dance_display ]]
        v_u_41 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.WebNPCShopUI:Clone()
        v_u_41.Name = v_u_1:gen_name(v_u_41.Name)
        v_u_41.Parent = v_u_10:get_world_ui_folder()
        v_u_40._native_size = v_u_41.PrimaryPart.Size
        v_u_40._size = v_u_40._native_size
        v_u_40:add_cycle_element(p_u_37, 1, v_u_6:new(v_u_5:new(v_u_40, v_u_41.PrimaryPart, v_u_41.BackButtonSurface), p_u_38, function() --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): p_u_39, (ref 2): v_u_40, (ref 3): p_u_37, (ref 4): v_u_8 ]]
            p_u_39:remove_menu(v_u_40)
            p_u_37._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
        end))
        v_u_40:add_cycle_element(p_u_37, 1, v_u_6:new(v_u_5:new(v_u_40, v_u_41.PrimaryPart, v_u_41.BuyButtonSurface), p_u_38, function() --[[ Line: 110 ]]
            --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_8, (ref 3): v_u_40 ]]
            p_u_37._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            v_u_40:buy_button_pressed()
        end)):set_passive_anim(true)
        v_u_40:add_cycle_element(p_u_37, 1, v_u_6:new(v_u_5:new(v_u_40, v_u_41.PrimaryPart, v_u_41.InfoButton), p_u_38, function() --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_8, (ref 3): p_u_39, (ref 4): v_u_22, (ref 5): p_u_38 ]]
            p_u_37._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            p_u_39:push_menu(v_u_22:new(p_u_37, p_u_38, p_u_39):set_text("Purchase NPC", "- All messages are subject to filter and moderation.\n- Your NPC will appear randomly at any time and location.\n- Gifts are only claimable once per player.\n- Messages are limited to 140 characters.\n- Only your previous 100 NPCs will be visible in your history.\n- Players will be able to vote and comment on your messages. View your NPCs to view any responses."))
        end))
        local l_TierButtons_0 = v_u_41.TierButtons
        local l_Proto_0 = l_TierButtons_0.Proto
        l_Proto_0.Parent = nil
        for v_u_50, v51 in v_u_2:new({
            [v_u_12.Tiers.Tier1] = l_TierButtons_0.Anchors.Tier1,
            [v_u_12.Tiers.Tier2] = l_TierButtons_0.Anchors.Tier2,
            [v_u_12.Tiers.Tier3] = l_TierButtons_0.Anchors.Tier3
        }):key_itr() do
            v51.Parent = nil
            local v52 = l_Proto_0:Clone()
            v52.CFrame = v51.CFrame
            v52.Parent = l_TierButtons_0
            local v53, v54 = v_u_12:tier_get_price_type_and_amount(v_u_50)
            local l_Frame_0 = v52.SurfaceGui.Frame
            v_u_14:currency_type_render_icon(v53, l_Frame_0.CurrencyIcon)
            l_Frame_0.PriceDisplay.Text = tostring(v54)
            l_Frame_0.DescriptionDisplay.Text = v_u_36:get(v_u_50)
            v_u_44:add(v_u_50, v_u_6:button_bind_anim_toggle(v_u_40:add_cycle_element(p_u_37, 1, v_u_6:new(v_u_5:new(v_u_40, v_u_41.PrimaryPart, v52), p_u_38, function() --[[ Line: 155 ]]
                --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_8, (ref 3): v_u_40, (copy 4): v_u_50 ]]
                p_u_37._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                v_u_40:tier_button_pressed(v_u_50)
            end)):set_auto_zoffset_behaviour(true), function() --[[ Line: 161 ]]
                --[[ Upvalues: (ref 1): v_u_40 ]]
                return v_u_40:get_alpha();
            end))
        end;
        for v55, v56 in v_u_44:key_itr() do
            v56:set_toggle(v55 == l_Tier1_0)
        end;
        v_u_40:add_cycle_element(p_u_37, 1, v_u_6:new(v_u_5:new(v_u_40, v_u_41.PrimaryPart, v_u_41.ViewNPCButton), p_u_38, function() --[[ Line: 170 ]]
            --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_8, (ref 3): v_u_35 ]]
            p_u_37._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            v_u_35:show_my_web_npcs(p_u_37)
        end)):set_auto_zoffset_behaviour(true)
        v_u_40:add_cycle_element(p_u_37, 1, v_u_6:new(v_u_5:new(v_u_40, v_u_41.PrimaryPart, v_u_41.ViewRecentButton), p_u_38, function() --[[ Line: 179 ]]
            --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_8, (ref 3): v_u_35 ]]
            p_u_37._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            v_u_35:show_recent_web_npcs(p_u_37)
        end)):set_auto_zoffset_behaviour(true)
        v_u_49 = v_u_11:new(p_u_37, v_u_41.PrimaryPart.SurfaceGui.Frame.Dialogue.TextDisplay, nil, v_u_40, p_u_38):set_empty_message("Enter your message here..."):set_send_behaviour_enabled(false):set_max_length(140)
        v_u_47 = v_u_41.SelectDanceButton.SurfaceGui.Frame.NameDisplay
        v_u_48 = v_u_41.SelectDanceButton.SurfaceGui.Frame.Icon
        v_u_40:add_cycle_element(p_u_37, 1, v_u_6:new(v_u_5:new(v_u_40, v_u_41.PrimaryPart, v_u_41.SelectDanceButton), p_u_38, function() --[[ Line: 203 ]]
            --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_8, (ref 3): v_u_40 ]]
            p_u_37._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            v_u_40:select_dance_button_pressed()
        end))
        f_update_selected_dance_display()
        for v57, v58 in v_u_44:key_itr() do
            v58:set_toggle(v57 == l_Tier1_0)
        end;
        v_u_40:reset_selected_item()
        v_u_40:transition_update_visual(0)
        v_u_40:layout()
    end;
    v_u_40.buy_button_pressed = function(p_u_59) --[[ Name: buy_button_pressed ]] --[[ Line: 216 ]]
        --[[ Upvalues: (ref 1): v_u_49, (copy 2): p_u_39, (ref 3): v_u_22, (copy 4): p_u_37, (copy 5): p_u_38, (ref 6): v_u_3, (ref 7): l_Tier1_0, (ref 8): l_SELECTED_DANCE_RANDOM_0, (ref 9): v_u_8, (ref 10): v_u_12, (ref 11): v_u_13 ]]
        local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 217 ]]
            --[[ Upvalues: (ref 1): v_u_49, (ref 2): p_u_39, (ref 3): v_u_22, (ref 4): p_u_37, (ref 5): p_u_38, (ref 6): v_u_3, (ref 7): l_Tier1_0, (ref 8): l_SELECTED_DANCE_RANDOM_0, (copy 9): p_u_59, (ref 10): v_u_8 ]]
            local function f_continue_to_purchase() --[[ Name: continue_to_purchase ]] --[[ Line: 219 ]]
                --[[ Upvalues: (ref 1): p_u_39, (ref 2): v_u_22, (ref 3): p_u_37, (ref 4): p_u_38, (ref 5): v_u_49, (ref 6): v_u_3, (ref 7): l_Tier1_0, (ref 8): l_SELECTED_DANCE_RANDOM_0, (ref 9): p_u_59, (ref 10): v_u_8 ]]
                local v_u_60 = p_u_39:push_menu(v_u_22:new(p_u_37, p_u_38, p_u_39):set_text("Purchasing...", "Please wait..."):set_close_button_visible(false))
                local v61 = v_u_49:get_current_text()
                if #v61 == 0 then
                    v61 = v_u_3:new():push_back_table_list({
                        "I couldn\'t think a message so here I am!",
                        "Rather be playing robeats right now...",
                        "trade boosts pls",
                        "give stars pls",
                        "Insight is the best map"
                    }):random()
                end;
                p_u_37._shop_local_protocol:buy_webnpc(l_Tier1_0, v61, l_SELECTED_DANCE_RANDOM_0, function(p62, p63) --[[ Line: 234 ]]
                    --[[ Upvalues: (ref 1): p_u_39, (copy 2): v_u_60, (ref 3): p_u_59, (ref 4): v_u_22, (ref 5): p_u_37, (ref 6): p_u_38, (ref 7): v_u_8 ]]
                    if p62 == false then
                        p_u_39:remove_menu(v_u_60)
                        p_u_39:remove_menu(p_u_59)
                        p_u_39:push_menu(v_u_22:new(p_u_37, p_u_38, p_u_39):set_text("Purchase Failed", p63))
                    else
                        p_u_37._player_blob_manager:do_sync(function(_) --[[ Line: 242 ]]
                            --[[ Upvalues: (ref 1): p_u_39, (ref 2): v_u_60, (ref 3): p_u_59, (ref 4): v_u_22, (ref 5): p_u_37, (ref 6): p_u_38, (ref 7): v_u_8 ]]
                            p_u_39:remove_menu(v_u_60)
                            p_u_39:remove_menu(p_u_59)
                            p_u_39:push_menu(v_u_22:new(p_u_37, p_u_38, p_u_39):set_text("Bought!", "Your NPC will appear in the city soon!"))
                            p_u_37._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                        end)
                    end;
                end)
            end;
            if #v_u_49:get_current_text() == 0 then
                p_u_39:push_menu(v_u_22:new(p_u_37, p_u_38, p_u_39):set_text("Empty Message", "Your message was empty. Continue with placeholder?")):set_okay_button_fn(function() --[[ Line: 260 ]]
                    --[[ Upvalues: (copy 1): f_continue_to_purchase ]]
                    f_continue_to_purchase()
                end)
            else
                f_continue_to_purchase()
            end;
        end;
        local v64 = p_u_37._player_blob_manager:get_player_blob()
        local v65, v66 = v_u_12:tier_get_price_type_and_amount(l_Tier1_0)
        local v67 = v_u_13:playerblob_purchase_needs_redirect(v64, v65, v66)
        if v67:is_valid() then
            v_u_13:show_purchase_redirect(p_u_37, v67, function(p68) --[[ Line: 272 ]]
                --[[ Upvalues: (copy 1): f_do_purchase ]]
                if p68 then
                    f_do_purchase()
                end;
            end)
        else
            f_do_purchase()
        end;
    end;
    v_u_40.tier_button_pressed = function(_, p69) --[[ Name: tier_button_pressed ]] --[[ Line: 282 ]]
        --[[ Upvalues: (ref 1): l_Tier1_0, (copy 2): v_u_44 ]]
        l_Tier1_0 = p69
        for v70, v71 in v_u_44:key_itr() do
            v71:set_toggle(v70 == l_Tier1_0)
        end;
    end;
    v_u_40.behaviour_update = function(p72, p73, _) --[[ Name: behaviour_update ]] --[[ Line: 287 ]]
        --[[ Upvalues: (copy 1): p_u_37, (ref 2): v_u_49, (ref 3): v_u_7 ]]
        p72:behaviour_update_base(p73, p_u_37)
        v_u_49:update(p73)
        local v74, v75 = v_u_49:get_raise_text_sent()
        if v74 == true then
            v_u_7:puts("text sent: %s", v75)
        end;
    end;
    v_u_40.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 297 ]]
        --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_41 ]]
        v_u_49:cleanup()
        v_u_41:Destroy()
    end;
    v_u_40.select_dance_button_pressed = function(_) --[[ Name: select_dance_button_pressed ]] --[[ Line: 302 ]]
        --[[ Upvalues: (copy 1): p_u_39, (ref 2): v_u_24, (copy 3): p_u_37, (copy 4): p_u_38, (ref 5): v_u_12, (ref 6): v_u_16, (ref 7): v_u_15, (ref 8): v_u_17, (ref 9): v_u_1, (ref 10): v_u_8, (ref 11): l_SELECTED_DANCE_RANDOM_0, (copy 12): f_update_selected_dance_display, (ref 13): v_u_23 ]]
        local v_u_76 = nil
        v_u_76 = p_u_39:push_menu(v_u_24:new(p_u_37, p_u_38, p_u_39, function(p77) --[[ Line: 305 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_37, (ref 3): v_u_16, (ref 4): v_u_15 ]]
            p77:set_header_text(string.format("Select Dance"))
            local v78 = p77:get_element_list()
            v78:push_back(v_u_12.SELECTED_DANCE_RANDOM)
            local v79 = v_u_16:get_owned_danceid_to_equipped_dict((p_u_37._player_blob_manager:get_player_blob()))
            for v80, _ in v_u_15:singleton():key_itr() do
                if v79:contains(v80) and v79:get(v80) == true then
                    v78:push_back(v80)
                end;
            end;
        end, function(p81, p82, p83, _, _) --[[ Line: 318 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_17, (ref 3): v_u_1 ]]
            if v_u_15:singleton():contains_dance_for_id(p81) then
                p82.Text = v_u_15:singleton():get_dance_name_for_id(p81)
                p82.TextColor3 = v_u_17:rarity_to_color(v_u_15:singleton():get_dance_rarity_for_id(p81))
                p83.Image = v_u_15:singleton():get_dance_icon_for_id(p81)
            else
                p82.Text = "Random"
                p82.TextColor3 = Color3.fromRGB(255, 255, 255)
                p83.Image = v_u_1:get_question_assetid()
            end;
        end, function(p_u_84) --[[ Line: 329 ]]
            --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_8, (ref 3): l_SELECTED_DANCE_RANDOM_0, (ref 4): f_update_selected_dance_display, (ref 5): p_u_39, (ref 6): v_u_76, (ref 7): v_u_15, (ref 8): v_u_23, (ref 9): p_u_38, (ref 10): v_u_1 ]]
            if p_u_84 ~= nil then
                local v_u_85 = nil
                local function f_set_selected_dance_id() --[[ Name: set_selected_dance_id ]] --[[ Line: 334 ]]
                    --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_8, (ref 3): l_SELECTED_DANCE_RANDOM_0, (copy 4): p_u_84, (ref 5): f_update_selected_dance_display, (ref 6): v_u_85, (ref 7): p_u_39, (ref 8): v_u_76 ]]
                    p_u_37._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                    l_SELECTED_DANCE_RANDOM_0 = p_u_84
                    f_update_selected_dance_display()
                    if v_u_85 then
                        p_u_39:remove_menu(v_u_85)
                    end;
                    p_u_39:remove_menu(v_u_76)
                end;
                if v_u_15:singleton():contains_dance_for_id(p_u_84) ~= true then
                    return f_set_selected_dance_id();
                end;
                v_u_85 = p_u_39:push_menu(v_u_23:new(p_u_37, p_u_38, p_u_39))
                local v86 = v_u_85:get_character_display()
                v86:push_animation_assetid(v_u_15:singleton():get_dance_assetid_for_id(p_u_84))
                v86:set_dance_active(true)
                v86:play_selected_animation()
                v_u_85:set_text(string.format("Dance: %s", v_u_15:singleton():get_dance_name_for_id(p_u_84)), "Select this dance for your NPC to perform.")
                local v_u_87 = v_u_85:get_action_buttons():pop_back()
                if v_u_87 then
                    v_u_87:set_visible(true)
                    local function _() --[[ Name: update_button_text ]] --[[ Line: 360 ]]
                        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_87 ]]
                        for _, v88 in v_u_1:get_list_of_children_of_classname(v_u_87:get_part(), "TextLabel"):key_itr() do
                            v88.Text = "Select Dance"
                        end;
                    end;
                    local v_u_89 = v_u_85
                    for _, v90 in v_u_1:get_list_of_children_of_classname(v_u_87:get_part(), "TextLabel"):key_itr() do
                        v90.Text = "Select Dance"
                    end;
                    v_u_87:bind_data(function() --[[ Line: 367 ]]
                        --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_8, (ref 3): l_SELECTED_DANCE_RANDOM_0, (copy 4): p_u_84, (ref 5): f_update_selected_dance_display, (ref 6): v_u_89, (ref 7): p_u_39, (ref 8): v_u_76 ]]
                        p_u_37._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                        l_SELECTED_DANCE_RANDOM_0 = p_u_84
                        f_update_selected_dance_display()
                        if v_u_89 then
                            p_u_39:remove_menu(v_u_89)
                        end;
                        p_u_39:remove_menu(v_u_76)
                    end)
                end;
            end;
        end):set_close_on_element_select(false))
    end;
    v_u_40.layout = function(p91) --[[ Name: layout ]] --[[ Line: 376 ]]
        --[[ Upvalues: (copy 1): p_u_38, (ref 2): v_u_43, (ref 3): v_u_41 ]]
        p91:opt_rescale_to_max_nxy(p_u_38, 0.7, 0.7, v_u_43)
        local v92, v93 = p91:opt_update_cframe_params(p_u_38, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p91:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v92 == true then
            v_u_41:SetPrimaryPartCFrame(v93)
        end;
    end;
    v_u_40.set_alpha = function(_, p94) --[[ Name: set_alpha ]] --[[ Line: 388 ]]
        --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_1, (ref 3): v_u_41 ]]
        if v_u_42 ~= p94 then
            v_u_42 = p94
            v_u_1:r_set_alpha(v_u_41, v_u_42)
        end;
    end;
    v_u_40.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 394 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        return v_u_42;
    end;
    v_u_40.set_scale = function(_, p95) --[[ Name: set_scale ]] --[[ Line: 395 ]]
        --[[ Upvalues: (ref 1): v_u_43 ]]
        v_u_43 = p95
    end;
    v_u_40.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 396 ]]
        --[[ Upvalues: (ref 1): v_u_43 ]]
        return v_u_43;
    end;
    v_u_40.get_native_size = function(p96) --[[ Name: get_native_size ]] --[[ Line: 398 ]]
        return p96._native_size;
    end;
    v_u_40.get_size = function(p97) --[[ Name: get_size ]] --[[ Line: 401 ]]
        return p97._size;
    end;
    v_u_40.set_size = function(p98, p99) --[[ Name: set_size ]] --[[ Line: 404 ]]
        --[[ Upvalues: (ref 1): v_u_41 ]]
        p98._size = p99
        v_u_41.PrimaryPart.Size = Vector3.new(p99.X, p99.Y, 0)
    end;
    v_u_40.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 408 ]]
        --[[ Upvalues: (ref 1): v_u_41 ]]
        return v_u_41.PrimaryPart.Position;
    end;
    v_u_40.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 411 ]]
        --[[ Upvalues: (ref 1): v_u_41 ]]
        return v_u_41.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_40;
end;
v_u_35.show_npc_messages_menu = function(_, p_u_100, p_u_101, p_u_102) --[[ Name: show_npc_messages_menu ]] --[[ Line: 451 ]]
    --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_22, (copy 3): v_u_19, (copy 4): v_u_3, (copy 5): v_u_9, (copy 6): v_u_18, (copy 7): v_u_20, (copy 8): v_u_12, (copy 9): v_u_7, (ref 10): v_u_24, (ref 11): v_u_26, (copy 12): v_u_15, (copy 13): v_u_36, (copy 14): v_u_8, (copy 15): v_u_6, (copy 16): v_u_35 ]]
    if v_u_1:do_disable_chat() then
        p_u_100._menus:push_menu(v_u_22:new(p_u_100, p_u_100._spui, p_u_100._menus):set_text("Disabled", "Chat is disabled on this platform."))
    else
        (function(p103, p_u_104) --[[ Name: get_npc_id_messages ]] --[[ Line: 457 ]]
            --[[ Upvalues: (copy 1): p_u_100, (ref 2): v_u_22, (ref 3): v_u_19, (ref 4): v_u_3, (ref 5): p_u_101, (ref 6): v_u_9, (ref 7): v_u_18, (ref 8): v_u_20, (ref 9): v_u_12 ]]
            local v_u_105 = p_u_100._menus:push_menu(v_u_22:new(p_u_100, p_u_100._spui, p_u_100._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            local v_u_106 = v_u_19.Builder:new()
            local v_u_107 = v_u_3:new()
            local v_u_108 = false
            local v_u_109 = p_u_101
            v_u_106:begin()
            p_u_100._evt:wait_on_event_once(v_u_9.EVT_WebNPC_ServerResponseNPCMessages, function(p110) --[[ Line: 466 ]]
                --[[ Upvalues: (ref 1): v_u_107, (ref 2): v_u_18, (copy 3): v_u_106 ]]
                v_u_107 = v_u_18:table_to_list(p110)
                v_u_106:finish()
            end)
            p_u_100._evt:fire_event_to_server(v_u_9.EVT_WebNPC_ClientRequestNPCMessages, p103)
            if v_u_20.WebNPCDoDatastoreAPIRead == true then
                v_u_106:begin()
                p_u_100._evt:wait_on_event_once(v_u_9.EVT_WebNPC_ServerResponseWebNPCIDInfo, function(p111, p112) --[[ Line: 475 ]]
                    --[[ Upvalues: (ref 1): v_u_108, (ref 2): v_u_109, (ref 3): v_u_12, (copy 4): v_u_106 ]]
                    if p112 == true then
                        v_u_108 = true
                        v_u_109 = v_u_12.NPCData:from_table(p111)
                    end;
                    v_u_106:finish()
                end)
                p_u_100._evt:fire_event_to_server(v_u_9.EVT_WebNPC_ClientRequestWebNPCIDInfo, p103)
            end;
            v_u_106:wait_for_finish(function() --[[ Line: 485 ]]
                --[[ Upvalues: (ref 1): p_u_100, (copy 2): v_u_105, (copy 3): p_u_104, (ref 4): v_u_107, (ref 5): v_u_108, (ref 6): v_u_109 ]]
                p_u_100._menus:remove_menu(v_u_105)
                p_u_104(v_u_107, v_u_108, v_u_109)
            end)
        end)(p_u_101:get_webnpcid(), function(p_u_113, p114, p115) --[[ Line: 491 ]]
            --[[ Upvalues: (ref 1): p_u_101, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_18, (copy 5): p_u_100, (ref 6): v_u_24, (ref 7): v_u_26, (ref 8): v_u_15, (ref 9): v_u_22, (ref 10): v_u_36, (ref 11): v_u_9, (ref 12): v_u_8, (ref 13): v_u_6, (ref 14): v_u_35, (copy 15): p_u_102 ]]
            if p114 == true then
                p_u_101 = p115
                if v_u_1:is_dev_build() then
                    v_u_7:puts("get_npc_id_messages updated npc data")
                    print(p_u_101:to_table())
                end;
            end;
            local v_u_116 = v_u_18:new():set_player_id_name(p_u_101:get_userid(), p_u_101:get_name()):set_message_time(p_u_101:get_created_at()):set_message_text(p_u_101:get_message()):bind_local_extra_data(-1)
            local v_u_125 = p_u_100._menus:push_menu(v_u_24:new(p_u_100, p_u_100._spui, p_u_100._menus, function(p117) --[[ Line: 509 ]]
                --[[ Upvalues: (ref 1): p_u_101, (ref 2): p_u_113, (copy 3): v_u_116 ]]
                p117:set_header_text("NPC Responses")
                p117:set_sub_text(string.format("\240\159\145\141 %d  \240\159\146\172 %d", p_u_101:get_like_count(), p_u_113:count()))
                for v118 = 1, p_u_113:count() do
                    p117:get_element_list():push_back(p_u_113:get(v118))
                end;
                p117:get_element_list():push_back(v_u_116)
            end, function(p119, p120, p_u_121, _, p122) --[[ Line: 517 ]]
                --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_1 ]]
                p120.Text = v_u_18:get_message_text_with_cutoff_length(p119:get_message_text(), 48)
                p_u_121.Image = v_u_1:transparent_assetid()
                p122:get_description_display().Text = string.format("%s   \226\143\176 %s", p119:get_player_name(), os.date(nil, p119:get_message_time()))
                if p119:get_local_extra_data() == -1 then
                    p122:get_description_display().Text = "[NPC] " .. p122:get_description_display().Text
                end;
                v_u_1:get_user_thumbnail(p119:get_player_id(), function(p123, _) --[[ Line: 525 ]]
                    --[[ Upvalues: (copy 1): p_u_121 ]]
                    if p_u_121 ~= nil then
                        p_u_121.Image = p123
                    end;
                end, false)
                p122:set_select_button_text("View")
            end, function(p124) --[[ Line: 530 ]]
                --[[ Upvalues: (ref 1): v_u_26, (ref 2): p_u_100 ]]
                if p124 then
                    v_u_26:show_chat_message_data_popup(p_u_100, p124)
                end;
            end)):set_empty_message("No messages."):set_close_on_element_select(false):set_fn_info_button_pressed(function() --[[ Line: 538 ]]
                --[[ Upvalues: (ref 1): p_u_101, (ref 2): v_u_15, (ref 3): p_u_100, (ref 4): v_u_22, (ref 5): v_u_36 ]]
                p_u_100._menus:push_menu(v_u_22:new(p_u_100, p_u_100._spui, p_u_100._menus):set_text(string.format("NPC Info"), string.format("Message: %s\n\nID: %d\nPlayer: %s (%d)\nTier: %s\nDance: %s\n\226\143\176 %s", p_u_101:get_message(), p_u_101:get_webnpcid(), p_u_101:get_name(), p_u_101:get_userid(), v_u_36:get(p_u_101:get_tier()), (typeof(p_u_101:get_danceid()) ~= "number" or not v_u_15:singleton():contains_dance_for_id(p_u_101:get_danceid())) and "Random" or v_u_15:singleton():get_dance_name_for_id(p_u_101:get_danceid()), os.date(nil, p_u_101:get_created_at()))))
            end)
            v_u_125:set_settings_section_visible()
            if v_u_125:get_settings_buttons():count() > 0 then
                local v126 = v_u_125:get_settings_buttons():pop_front()
                v126:set_visible(true)
                v126:bind_data(function() --[[ Line: 565 ]]
                    --[[ Upvalues: (ref 1): v_u_26, (ref 2): p_u_100, (ref 3): v_u_22, (ref 4): v_u_9, (ref 5): p_u_101, (ref 6): p_u_113, (ref 7): v_u_18, (copy 8): v_u_125, (ref 9): v_u_8 ]]
                    v_u_26:show_post_chat_message_menu(p_u_100, function(p127) --[[ Line: 566 ]]
                        --[[ Upvalues: (ref 1): p_u_100, (ref 2): v_u_22, (ref 3): v_u_9, (ref 4): p_u_101, (ref 5): p_u_113, (ref 6): v_u_18, (ref 7): v_u_125, (ref 8): v_u_8 ]]
                        if typeof(p127) == "string" then
                            if #p127 ~= 0 then
                                local v_u_128 = p_u_100._menus:push_menu(v_u_22:new(p_u_100, p_u_100._spui, p_u_100._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                                p_u_100._evt:wait_on_event_once(v_u_9.EVT_WebNPC_ServerPostNPCMessageResponse, function(p_u_129, p_u_130, p_u_131, p132) --[[ Line: 571 ]]
                                    --[[ Upvalues: (ref 1): p_u_100, (copy 2): v_u_128, (ref 3): v_u_22, (ref 4): p_u_101, (ref 5): p_u_113, (ref 6): v_u_18, (ref 7): v_u_125, (ref 8): v_u_8 ]]
                                    local function f_fin() --[[ Name: fin ]] --[[ Line: 572 ]]
                                        --[[ Upvalues: (ref 1): p_u_100, (ref 2): v_u_128, (copy 3): p_u_129, (ref 4): v_u_22, (copy 5): p_u_130, (ref 6): p_u_101, (ref 7): p_u_113, (ref 8): v_u_18, (copy 9): p_u_131, (ref 10): v_u_125, (ref 11): v_u_8 ]]
                                        p_u_100._menus:remove_menu(v_u_128)
                                        if p_u_129 then
                                            p_u_101:set_comment_count(p_u_101:get_comment_count() + 1)
                                            p_u_113 = v_u_18:table_to_list(p_u_131)
                                            v_u_125:refresh()
                                        else
                                            p_u_100._menus:push_menu(v_u_22:new(p_u_100, p_u_100._spui, p_u_100._menus):set_text("Error", p_u_130))
                                        end;
                                        p_u_100._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                                    end;
                                    if p132 == true then
                                        p_u_100._player_blob_manager:do_sync(function() --[[ Line: 584 ]]
                                            --[[ Upvalues: (copy 1): f_fin ]]
                                            f_fin()
                                        end)
                                    else
                                        f_fin()
                                    end;
                                end)
                                p_u_100._evt:fire_event_to_server(v_u_9.EVT_WebNPC_ClientPostNPCMessage, p_u_101:get_webnpcid(), p127)
                            end;
                        else
                            return;
                        end;
                    end)
                end)
                v_u_6:set_button_text(v126, "\240\159\146\172 Post")
            end;
            if v_u_125:get_settings_buttons():count() > 0 then
                local v_u_133 = v_u_125:get_settings_buttons():pop_front()
                local function _() --[[ Name: update_like_button_enabled ]] --[[ Line: 601 ]]
                    --[[ Upvalues: (copy 1): v_u_133, (ref 2): p_u_100, (ref 3): p_u_101 ]]
                    v_u_133:set_enabled(p_u_100._player_blob_manager:get_liked_web_npc_id_set():contains(p_u_101:get_webnpcid()) ~= true)
                end;
                v_u_133:set_visible(true)
                v_u_133:bind_data(function() --[[ Line: 606 ]]
                    --[[ Upvalues: (ref 1): v_u_35, (ref 2): p_u_100, (ref 3): p_u_101, (copy 4): v_u_133, (copy 5): v_u_125 ]]
                    v_u_35:webnpc_do_like(p_u_100, p_u_101, function() --[[ Line: 607 ]]
                        --[[ Upvalues: (ref 1): v_u_133, (ref 2): p_u_100, (ref 3): p_u_101, (ref 4): v_u_125 ]]
                        v_u_133:set_enabled(p_u_100._player_blob_manager:get_liked_web_npc_id_set():contains(p_u_101:get_webnpcid()) ~= true)
                        v_u_125:refresh()
                    end)
                end)
                v_u_6:set_button_text(v_u_133, "\240\159\145\141 Like")
                v_u_6:button_add_enabled_anim(v_u_133, function() --[[ Line: 613 ]]
                    --[[ Upvalues: (copy 1): v_u_125 ]]
                    return v_u_125:get_alpha();
                end)
                v_u_133:set_enabled(p_u_100._player_blob_manager:get_liked_web_npc_id_set():contains(p_u_101:get_webnpcid()) ~= true)
            end;
            if p_u_102 then
                p_u_102(v_u_125)
            end;
        end)
    end;
end;
local function f_create_npcs_list_ui(p_u_134, p_u_135, _) --[[ Name: create_npcs_list_ui ]] --[[ Line: 624 ]]
    --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_18, (copy 3): v_u_1, (copy 4): v_u_12, (copy 5): v_u_35 ]]
    return p_u_134._menus:push_menu(v_u_24:new(p_u_134, p_u_134._spui, p_u_134._menus, function(p136) --[[ Line: 627 ]]
        --[[ Upvalues: (copy 1): p_u_135 ]]
        for _, v137 in p_u_135:key_itr() do
            p136:get_element_list():push_back(v137)
        end;
    end, function(p138, p139, p_u_140, _, p141) --[[ Line: 632 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_1, (ref 3): v_u_12 ]]
        p139.Text = v_u_18:get_message_text_with_cutoff_length(p138:get_message(), 48)
        v_u_1:get_user_thumbnail(p138:get_userid(), function(p142, _) --[[ Line: 634 ]]
            --[[ Upvalues: (copy 1): p_u_140 ]]
            if p_u_140 ~= nil then
                p_u_140.Image = p142
            end;
        end, false)
        p141:set_select_button_text("View")
        p141:get_description_display().Text = string.format("%s \240\159\145\164 %s - \226\143\176 %s", v_u_12:tier_to_emoji(p138:get_tier()), p138:get_name(), os.date(nil, p138:get_created_at()))
    end, function(p143) --[[ Line: 645 ]]
        --[[ Upvalues: (ref 1): v_u_35, (copy 2): p_u_134 ]]
        if p143 ~= nil then
            v_u_35:show_npc_messages_menu(p_u_134, p143)
        end;
    end):set_close_on_element_select(false));
end;
v_u_35.show_my_web_npcs = function(_, p_u_144) --[[ Name: show_my_web_npcs ]] --[[ Line: 655 ]]
    --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_22, (copy 3): v_u_9, (copy 4): v_u_12, (copy 5): f_create_npcs_list_ui ]]
    if v_u_1:do_disable_chat() then
        p_u_144._menus:push_menu(v_u_22:new(p_u_144, p_u_144._spui, p_u_144._menus):set_text("Disabled", "Chat is disabled on this platform."))
    else
        (function(p_u_145) --[[ Name: get_my_npcs_list ]] --[[ Line: 661 ]]
            --[[ Upvalues: (copy 1): p_u_144, (ref 2): v_u_22, (ref 3): v_u_9, (ref 4): v_u_12 ]]
            local v_u_146 = p_u_144._menus:push_menu(v_u_22:new(p_u_144, p_u_144._spui, p_u_144._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_144._evt:wait_on_event_once(v_u_9.EVT_WebNPC_ServerResponseMyNPCs, function(p147) --[[ Line: 663 ]]
                --[[ Upvalues: (ref 1): p_u_144, (copy 2): v_u_146, (ref 3): v_u_12, (copy 4): p_u_145 ]]
                p_u_144._menus:remove_menu(v_u_146)
                p_u_145((v_u_12.NPCData:table_to_list(p147)))
            end)
            p_u_144._evt:fire_event_to_server(v_u_9.EVT_WebNPC_ClientRequestMyNPCs)
        end)(function(p148) --[[ Line: 671 ]]
            --[[ Upvalues: (ref 1): f_create_npcs_list_ui, (copy 2): p_u_144 ]]
            f_create_npcs_list_ui(p_u_144, p148):set_header_text(string.format("My NPCs")):set_empty_message("You haven\'t created any NPCs yet.")
        end)
    end;
end;
v_u_35.show_recent_web_npcs = function(_, p_u_149) --[[ Name: show_recent_web_npcs ]] --[[ Line: 678 ]]
    --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_22, (copy 3): v_u_9, (copy 4): v_u_12, (copy 5): f_create_npcs_list_ui ]]
    if v_u_1:do_disable_chat() then
        p_u_149._menus:push_menu(v_u_22:new(p_u_149, p_u_149._spui, p_u_149._menus):set_text("Disabled", "Chat is disabled on this platform."))
    else
        (function(p_u_150) --[[ Name: get_recent_npcs_list ]] --[[ Line: 684 ]]
            --[[ Upvalues: (copy 1): p_u_149, (ref 2): v_u_22, (ref 3): v_u_9, (ref 4): v_u_12 ]]
            local v_u_151 = p_u_149._menus:push_menu(v_u_22:new(p_u_149, p_u_149._spui, p_u_149._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_149._evt:wait_on_event_once(v_u_9.EVT_WebNPC_ServerResponseRecent, function(p152) --[[ Line: 686 ]]
                --[[ Upvalues: (ref 1): p_u_149, (copy 2): v_u_151, (ref 3): v_u_12, (copy 4): p_u_150 ]]
                p_u_149._menus:remove_menu(v_u_151)
                p_u_150((v_u_12.NPCData:table_to_list(p152)))
            end)
            p_u_149._evt:fire_event_to_server(v_u_9.EVT_WebNPC_ClientRequestRecent)
        end)(function(p153) --[[ Line: 694 ]]
            --[[ Upvalues: (ref 1): f_create_npcs_list_ui, (copy 2): p_u_149 ]]
            f_create_npcs_list_ui(p_u_149, p153):set_header_text(string.format("Recent NPCs")):set_empty_message("No recent NPCs.")
        end)
    end;
end;
return v_u_35;
