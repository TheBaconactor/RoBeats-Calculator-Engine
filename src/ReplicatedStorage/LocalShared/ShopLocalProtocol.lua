-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:00 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.Shared.QueueSequential)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Data)
return {
    ["new"] = function(_, p_u_8, p_u_9) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_7, (copy 5): v_u_5, (copy 6): v_u_1, (copy 7): v_u_6 ]]
        local v10 = {}
        local v_u_11 = v_u_4:new()
        local function _() --[[ Name: cons ]] --[[ Line: 19 ]]
            --[[ Upvalues: (copy 1): v_u_11 ]]
            for _, v12 in v_u_11:key_itr() do
                v12()
            end;
            v_u_11:clear()
        end;
        local v_u_13 = v_u_4:new()
        local v_u_14 = nil
        local v_u_15 = -1
        v10.request_shop_info = function(_, p16) --[[ Name: request_shop_info ]] --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): v_u_13, (copy 2): p_u_9, (ref 3): v_u_2, (ref 4): v_u_14 ]]
            v_u_13:push_back(p16)
            if v_u_13:count() == 1 then
                p_u_9:wait_on_event_once(v_u_2.EVT_Shop_ServerInfoResponse, function(p17, p18) --[[ Line: 33 ]]
                    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_13 ]]
                    v_u_14 = p17
                    for _, v19 in v_u_13:key_itr() do
                        v19(p17, p18)
                    end;
                    v_u_13:clear()
                end)
                p_u_9:fire_event_to_server(v_u_2.EVT_Shop_ClientInfoRequest)
            end;
        end;
        v10.request_shop_info_cached = function(p20, p_u_21) --[[ Name: request_shop_info_cached ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_8, (ref 3): v_u_14 ]]
            if v_u_15 ~= p_u_8._player_blob_manager:get_day_id() then
                v_u_15 = p_u_8._player_blob_manager:get_day_id()
                v_u_14 = nil
            end;
            if v_u_14 == nil then
                p20:request_shop_info(function(p22, _) --[[ Line: 53 ]]
                    --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_8, (ref 3): v_u_14, (copy 4): p_u_21 ]]
                    v_u_15 = p_u_8._player_blob_manager:get_day_id()
                    v_u_14 = p22
                    p_u_21(p22)
                end)
            else
                p_u_21(v_u_14)
            end;
        end;
        v10.try_purchase_saleitem = function(_, p23, p_u_24) --[[ Name: try_purchase_saleitem ]] --[[ Line: 62 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Shop_ServerAttemptPurchaseSaleResponse, function(p25, p26) --[[ Line: 63 ]]
                --[[ Upvalues: (copy 1): p_u_24 ]]
                if p25 == true then
                    p_u_24(true, "", p26)
                else
                    p_u_24(false, p26, -1)
                end;
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Shop_ClientAttemptPurchaseSale, p23)
        end;
        v10.request_gatcha_info = function(_, p_u_27) --[[ Name: request_gatcha_info ]] --[[ Line: 73 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Shop_ServerSongGatchaInfoResponse, function(p28) --[[ Line: 74 ]]
                --[[ Upvalues: (copy 1): p_u_27 ]]
                p_u_27(p28)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Shop_ClientSongGatchaInfoRequest)
        end;
        v10.try_purchase_gatcha = function(_, p29, p30, p_u_31) --[[ Name: try_purchase_gatcha ]] --[[ Line: 80 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Shop_ServerSongGatchaAttemptResponse, function(p32, p33, p34) --[[ Line: 81 ]]
                --[[ Upvalues: (copy 1): p_u_31 ]]
                p_u_31(p32, p33, p34)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Shop_ClientSongGatchaAttempt, p29, p30)
        end;
        v10.request_currency_purchase_info = function(_, p_u_35) --[[ Name: request_currency_purchase_info ]] --[[ Line: 87 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Shop_ServerCurrencyPurchaseInfoResponse, function(p36) --[[ Line: 88 ]]
                --[[ Upvalues: (copy 1): p_u_35 ]]
                p_u_35(p36)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Shop_ClientCurrencyPurchaseInfoRequest)
        end;
        v10.request_currency_purchase_info_v3 = function(_, p_u_37) --[[ Name: request_currency_purchase_info_v3 ]] --[[ Line: 94 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Shop_ServerCurrencyPurchaseInfoResponse_V3, function(p38) --[[ Line: 95 ]]
                --[[ Upvalues: (copy 1): p_u_37 ]]
                p_u_37(p38)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Shop_ClientCurrencyPurchaseInfoRequest_V3)
        end;
        v10.try_combine_song = function(_, p39, p_u_40) --[[ Name: try_combine_song ]] --[[ Line: 101 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Shop_ServerCombineSongAttemptResponse, function(p41, p42, p43) --[[ Line: 102 ]]
                --[[ Upvalues: (copy 1): p_u_40 ]]
                p_u_40(p41, p42, p43)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Shop_ClientCombineSongAttempt, p39)
        end;
        v10.request_gear_shop_info = function(_, p_u_44) --[[ Name: request_gear_shop_info ]] --[[ Line: 108 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_GearShop_ServerInfoResponse, function(p45, p46) --[[ Line: 109 ]]
                --[[ Upvalues: (copy 1): p_u_44 ]]
                p_u_44(p45, p46)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_GearShop_ClientInfoRequest)
        end;
        local v_u_47 = nil
        local v_u_48 = -1
        v10.request_gear_shop_info_cached = function(p49, p_u_50) --[[ Name: request_gear_shop_info_cached ]] --[[ Line: 118 ]]
            --[[ Upvalues: (ref 1): v_u_48, (copy 2): p_u_8, (ref 3): v_u_47 ]]
            if v_u_48 ~= p_u_8._player_blob_manager:get_day_id() then
                v_u_48 = p_u_8._player_blob_manager:get_day_id()
                v_u_47 = nil
            end;
            if v_u_47 == nil then
                p49:request_gear_shop_info(function(p51, _) --[[ Line: 127 ]]
                    --[[ Upvalues: (ref 1): v_u_48, (ref 2): p_u_8, (ref 3): v_u_47, (copy 4): p_u_50 ]]
                    v_u_48 = p_u_8._player_blob_manager:get_day_id()
                    v_u_47 = p51
                    p_u_50(p51)
                end)
            else
                p_u_50(v_u_47)
            end;
        end;
        v10.try_purchase_gear_shop_saleitem = function(_, p52, p_u_53) --[[ Name: try_purchase_gear_shop_saleitem ]] --[[ Line: 136 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_GearShop_ServerAttemptPurchaseSaleResponse, function(p54, p55, p56, p57) --[[ Line: 137 ]]
                --[[ Upvalues: (copy 1): p_u_53 ]]
                p_u_53(p54, p55, p56, p57)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_GearShop_ClientAttemptPurchaseSale, p52)
        end;
        local v_u_58 = nil
        v10.request_challengepass_info = function(_, p_u_59) --[[ Name: request_challengepass_info ]] --[[ Line: 144 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2, (ref 3): v_u_58, (ref 4): v_u_3 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_ChallengePass_ServerRequestInfoResponse, function(p60, p61, p62) --[[ Line: 145 ]]
                --[[ Upvalues: (ref 1): v_u_58, (ref 2): v_u_3, (copy 3): p_u_59 ]]
                v_u_58 = v_u_3:json_to_challengepass_mission_list(p60)
                p_u_59(v_u_58, p61, p62)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_ChallengePass_ClientRequestInfo)
        end;
        v10.request_challengepass_info_cached = function(p63, p_u_64) --[[ Name: request_challengepass_info_cached ]] --[[ Line: 152 ]]
            --[[ Upvalues: (ref 1): v_u_58 ]]
            if v_u_58 == nil then
                p63:request_challengepass_info(function(p65, _, _) --[[ Line: 156 ]]
                    --[[ Upvalues: (copy 1): p_u_64 ]]
                    p_u_64(p65)
                end)
            else
                p_u_64(v_u_58)
            end;
        end;
        local v_u_66 = v_u_4:new()
        local v_u_67 = nil
        local v_u_68 = -1
        v10.request_challengepassv2_entry_list = function(_, p69) --[[ Name: request_challengepassv2_entry_list ]] --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): v_u_67, (copy 2): p_u_8, (ref 3): v_u_68, (copy 4): v_u_66, (ref 5): v_u_2, (ref 6): v_u_7 ]]
            if v_u_67 == nil or p_u_8._player_blob_manager:get_day_id() ~= v_u_68 then
                if v_u_66:count() == 0 then
                    v_u_66:push_back(p69)
                    p_u_8._evt:wait_on_event_once(v_u_2.EVT_ChallengePassV2_ServerRequestInfoResponse, function(p70) --[[ Line: 175 ]]
                        --[[ Upvalues: (ref 1): v_u_67, (ref 2): v_u_7, (ref 3): v_u_68, (ref 4): p_u_8, (ref 5): v_u_66 ]]
                        v_u_67 = v_u_7:entry_list_from_table(p70)
                        v_u_68 = p_u_8._player_blob_manager:get_day_id()
                        for _, v71 in v_u_66:key_itr() do
                            v71(v_u_67)
                        end;
                        v_u_66:clear()
                    end)
                    p_u_8._evt:fire_event_to_server(v_u_2.EVT_ChallengePassV2_ClientRequestInfo)
                else
                    v_u_66:push_back(p69)
                end;
            else
                p69(v_u_67)
                return;
            end;
        end;
        v10.claim_mission_complete = function(_, p72, p73, p_u_74) --[[ Name: claim_mission_complete ]] --[[ Line: 187 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Mission_ServerClaimMissionCompleteResponse, function(p75, p76) --[[ Line: 188 ]]
                --[[ Upvalues: (copy 1): p_u_74 ]]
                p_u_74(p75, p76)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Mission_ClientClaimMissionComplete, p72, p73)
        end;
        v10.buy_webnpc = function(_, p77, p78, p79, p_u_80) --[[ Name: buy_webnpc ]] --[[ Line: 194 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_WebNPC_ServerAttemptPurchaseResponse, function(p81, p82) --[[ Line: 195 ]]
                --[[ Upvalues: (copy 1): p_u_80 ]]
                p_u_80(p81, p82)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_WebNPC_ClientAttemptPurchase, p77, p78, p79)
        end;
        v10.visit_webnpc = function(_, p83, p_u_84) --[[ Name: visit_webnpc ]] --[[ Line: 201 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_WebNPC_ServerAcknowledgeClientVisitNPC, function(p85, p86, p87) --[[ Line: 202 ]]
                --[[ Upvalues: (copy 1): p_u_84 ]]
                p_u_84(p85, p86, p87)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_WebNPC_ClientVisitNPC, p83)
        end;
        v10.try_sell_song = function(_, p88, p_u_89) --[[ Name: try_sell_song ]] --[[ Line: 208 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Shop_ServerSellSongAttemptResponse, function(p90, p91, p92) --[[ Line: 209 ]]
                --[[ Upvalues: (copy 1): p_u_89 ]]
                p_u_89(p90, p91, p92)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Shop_ClientSellSongAttempt, p88)
        end;
        v10.try_craft_song_recipe = function(_, p93, p_u_94, p95) --[[ Name: try_craft_song_recipe ]] --[[ Line: 215 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            local v96 = p95 == nil and 1 or p95
            p_u_9:wait_on_event_once(v_u_2.EVT_Crafting_CraftSongServerResponse, function(p97, p98) --[[ Line: 218 ]]
                --[[ Upvalues: (copy 1): p_u_94 ]]
                p_u_94(p97, p98)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Crafting_CraftSongClientRequest, p93, v96)
        end;
        v10.request_crafting_gatcha_info = function(_, p_u_99) --[[ Name: request_crafting_gatcha_info ]] --[[ Line: 224 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Crafting_ServerCraftGatchaInfoResponse, function(p100) --[[ Line: 225 ]]
                --[[ Upvalues: (copy 1): p_u_99 ]]
                p_u_99(p100)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Crafting_ClientCraftGatchaInfoRequest)
        end;
        v10.try_purchase_crafting_gatcha = function(_, p101, p_u_102) --[[ Name: try_purchase_crafting_gatcha ]] --[[ Line: 231 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Crafting_ServerCraftGatchaAttemptResponse, function(p103, p104, p105) --[[ Line: 232 ]]
                --[[ Upvalues: (copy 1): p_u_102 ]]
                p_u_102(p103, p104, p105)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Crafting_ClientCraftGatchaAttempt, p101)
        end;
        v10.try_craft_gear_upgrade = function(_, p106, p107, p_u_108) --[[ Name: try_craft_gear_upgrade ]] --[[ Line: 238 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Crafting_CraftGearUpgradeServerResponse, function(p109, p110, p111) --[[ Line: 239 ]]
                --[[ Upvalues: (copy 1): p_u_108 ]]
                p_u_108(p109, p110, p111)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Crafting_CraftGearUpgradeClientRequest, p106, p107)
        end;
        v10.try_craft_gear_boost_upgrade = function(_, p112, p113, p114, p115, p_u_116) --[[ Name: try_craft_gear_boost_upgrade ]] --[[ Line: 245 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Crafting_CraftGearBoostUpgradeServerResponse, function(p117, p118, p119, p120, p121) --[[ Line: 246 ]]
                --[[ Upvalues: (copy 1): p_u_116 ]]
                p_u_116(p117, p118, p119, p120, p121)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Crafting_CraftGearBoostUpgradeClientRequest, p112, p113, p114, p115)
        end;
        v10.try_craft_gear = function(_, p122, p_u_123) --[[ Name: try_craft_gear ]] --[[ Line: 252 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Crafting_CraftGearServerResponse, function(p124, p125) --[[ Line: 253 ]]
                --[[ Upvalues: (copy 1): p_u_123 ]]
                p_u_123(p124, p125)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Crafting_CraftGearClientRequest, p122)
        end;
        v10.try_craft_material_recipe = function(_, p126, p127, p_u_128) --[[ Name: try_craft_material_recipe ]] --[[ Line: 259 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Crafting_CraftMaterialServerResponse, function(p129, p130, p131) --[[ Line: 260 ]]
                --[[ Upvalues: (copy 1): p_u_128 ]]
                p_u_128(p129, p130, p131)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Crafting_CraftMaterialClientRequest, p126, p127)
        end;
        v10.try_delete_gear = function(_, p132, p_u_133) --[[ Name: try_delete_gear ]] --[[ Line: 266 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Lobby_ServerResponseDeleteGear, function(p134, p135) --[[ Line: 267 ]]
                --[[ Upvalues: (copy 1): p_u_133 ]]
                p_u_133(p134, p135)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Lobby_ClientRequestDeleteGear, p132)
        end;
        v10.request_dance_shop_info = function(_, p_u_136) --[[ Name: request_dance_shop_info ]] --[[ Line: 273 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_DanceShop_ServerInfoResponse, function(p137, p138) --[[ Line: 274 ]]
                --[[ Upvalues: (copy 1): p_u_136 ]]
                p_u_136(p137, p138)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_DanceShop_ClientInfoRequest)
        end;
        v10.try_purchase_dance = function(_, p139, p_u_140) --[[ Name: try_purchase_dance ]] --[[ Line: 280 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_DanceShop_ServerAttemptPurchaseResponse, function(p141, p142, p143) --[[ Line: 281 ]]
                --[[ Upvalues: (copy 1): p_u_140 ]]
                p_u_140(p141, p142, p143)
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_DanceShop_ClientAttemptPurchase, p139)
        end;
        local v_u_144 = nil
        v_u_144 = v_u_5:new(function(p_u_145, p_u_146) --[[ Line: 288 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2, (ref 3): v_u_1, (ref 4): v_u_144 ]]
            p_u_9:wait_on_event_once(v_u_2.EVT_Leaderboard_ServerResponseQuerySongIndex, function(p147, p148, p149) --[[ Line: 289 ]]
                --[[ Upvalues: (copy 1): p_u_146, (ref 2): v_u_1, (copy 3): p_u_145, (ref 4): v_u_144 ]]
                if p147 == true then
                    p_u_146(p148, p149)
                else
                    v_u_1:warnf("EVT_Leaderboard_ServerResponseQuerySongIndex(%d) failed", (tonumber(p_u_145)))
                    v_u_144:force_active(false)
                    v_u_144:dequeue_and_apply()
                end;
            end)
            p_u_9:fire_event_to_server(v_u_2.EVT_Leaderboard_ClientQuerySongIndex, p_u_145)
        end)
        v10.leaderboard_query_song_index = function(_, p150, p_u_151) --[[ Name: leaderboard_query_song_index ]] --[[ Line: 300 ]]
            --[[ Upvalues: (ref 1): v_u_144 ]]
            v_u_144:queue_sequential(p150, function(p152, p153) --[[ Line: 301 ]]
                --[[ Upvalues: (copy 1): p_u_151 ]]
                p_u_151(p152, p153)
            end)
        end;
        local v_u_154 = -1
        local v_u_155 = v_u_6:new()
        v10.leaderboard_query_song_index_cached = function(p156, p_u_157, p_u_158) --[[ Name: leaderboard_query_song_index_cached ]] --[[ Line: 308 ]]
            --[[ Upvalues: (ref 1): v_u_154, (copy 2): p_u_8, (copy 3): v_u_155 ]]
            if v_u_154 ~= p_u_8._player_blob_manager:get_synced_time() then
                v_u_155:clear()
            end;
            if v_u_155:contains(p_u_157) then
                return p_u_158(v_u_155:get(p_u_157));
            end;
            p156:leaderboard_query_song_index(p_u_157, function(p159) --[[ Line: 317 ]]
                --[[ Upvalues: (ref 1): v_u_154, (ref 2): p_u_8, (ref 3): v_u_155, (copy 4): p_u_157, (copy 5): p_u_158 ]]
                v_u_154 = p_u_8._player_blob_manager:get_synced_time()
                v_u_155:add(p_u_157, p159)
                p_u_158(p159)
            end)
        end;
        local v_u_160 = v_u_4:new()
        local v_u_161 = 0
        v_u_11:push_back(function() --[[ Line: 326 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_2, (copy 3): v_u_160 ]]
            p_u_8._evt:wait_on_event(v_u_2.EVT_Marketplace_ServerQueryServerSalesResponse, function(p_u_162) --[[ Line: 328 ]]
                --[[ Upvalues: (ref 1): v_u_160 ]]
                spawn(function() --[[ Line: 329 ]]
                    --[[ Upvalues: (ref 1): v_u_160, (copy 2): p_u_162 ]]
                    wait(0.25)
                    for _, v163 in v_u_160:key_itr() do
                        v163(p_u_162)
                    end;
                    v_u_160:clear()
                end)
            end)
        end)
        v10.marketplace_query_sales = function(_, p164) --[[ Name: marketplace_query_sales ]] --[[ Line: 339 ]]
            --[[ Upvalues: (copy 1): v_u_160, (ref 2): v_u_161, (copy 3): p_u_8, (ref 4): v_u_2 ]]
            v_u_160:push_back(p164)
            if v_u_160:count() == 1 or tick() - v_u_161 > 5 then
                p_u_8._evt:fire_event_to_server(v_u_2.EVT_Marketplace_ClientQueryServerSales)
                v_u_161 = tick()
            end;
        end;
        for _, v165 in v_u_11:key_itr() do
            v165()
        end;
        v_u_11:clear()
        return v10;
    end
};
